from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONICLE_PATH = PROJECT_ROOT / "chronicle_data.json"
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "workflow" / "backups"

OPEN_TAG_RE = re.compile(r"\[([A-Za-z0-9 _-]+)\]")

LEGACY_TOP_LEVEL_TAGS = {
    "SEGMENT_NUMBER",
    "SEGMENT_SLUG",
    "ERA_SLUG",
    "TITLE",
    "LOCATION",
    "TAGLINE",
    "ADVENTURE_TEXT",
    "COMMENTARY",
    "SUMMARY",
    "STATE",
    "IMAGES",
}

TEMPLATE_TOP_LEVEL_TAGS = {
    "era number",
    "segment number",
    "segment title",
    "location",
    "tagline",
    "adventure text",
    "images",
    "commentary",
    "summary",
    "state",
}

TEMPLATE_IMAGE_SEQUENCE = (
    "image title",
    "image location",
    "image alt text",
    "image caption",
)

TEMPLATE_STATE_KEYS = (
    "Location",
    "Weapons",
    "Gear",
    "Objective",
)

STATE_TAGS = {
    "STATE_LOCATION": "Location",
    "STATE_WEAPONS": "Weapons",
    "STATE_GEAR": "Gear",
    "STATE_STATUS": "Status",
    "STATE_SPECIAL_ITEMS": "Special items",
    "STATE_OBJECTIVE": "Objective",
}


class PacketError(ValueError):
    pass


@dataclass(frozen=True)
class CommentEntry:
    speaker: str
    content: str


@dataclass(frozen=True)
class ImageEntry:
    src: str
    alt: str
    title: str
    caption: str


@dataclass(frozen=True)
class PacketData:
    segment_number: str
    segment_slug: str
    era_slug: str
    title: str
    location: str
    tagline: str
    adventure_text: list[str]
    commentary: list[CommentEntry]
    summary: str
    state: dict[str, str]
    images: list[ImageEntry]

    def to_segment_object(self) -> dict[str, object]:
        return {
            "slug": self.segment_slug,
            "number": self.segment_number,
            "title": self.title,
            "location": self.location,
            "tagline": self.tagline,
            "adventureText": self.adventure_text,
            "images": [
                {
                    "src": image.src,
                    "alt": image.alt,
                    "title": image.title,
                    "caption": image.caption,
                }
                for image in self.images
            ],
            "commentary": [
                {
                    "speaker": comment.speaker,
                    "content": comment.content,
                }
                for comment in self.commentary
            ],
            "summary": self.summary,
            "state": self.state,
        }


@dataclass(frozen=True)
class ImportResult:
    packet: PacketData
    segment_object: dict[str, object]
    chronicle_path: Path
    backup_path: Path | None = None


def _strip_outer_whitespace(value: str) -> str:
    return value.strip()


def _parse_tag_blocks(text: str, allowed_tags: Iterable[str], context: str) -> list[tuple[str, str]]:
    allowed = set(allowed_tags)
    blocks: list[tuple[str, str]] = []
    position = 0

    while True:
        while position < len(text) and text[position].isspace():
            position += 1

        if position >= len(text):
            break

        match = OPEN_TAG_RE.match(text, position)
        if not match:
            snippet = text[position : position + 40].replace("\n", "\\n")
            raise PacketError(f"{context}: expected an opening tag near '{snippet}'.")

        tag = match.group(1)
        if tag not in allowed:
            raise PacketError(f"{context}: unexpected tag [{tag}].")

        close_tag = f"[/{tag}]"
        body_start = match.end()
        body_end = text.find(close_tag, body_start)
        if body_end == -1:
            raise PacketError(f"{context}: missing closing tag {close_tag}.")

        blocks.append((tag, text[body_start:body_end]))
        position = body_end + len(close_tag)

    return blocks


def _single_required_block(
    blocks: list[tuple[str, str]],
    tag: str,
    context: str,
    allow_empty: bool = False,
) -> str:
    matches = [body for name, body in blocks if name == tag]
    if not matches:
        raise PacketError(f"{context}: missing required tag [{tag}].")
    if len(matches) > 1:
        raise PacketError(f"{context}: duplicate tag [{tag}].")
    value = _strip_outer_whitespace(matches[0])
    if not value and not allow_empty:
        raise PacketError(f"{context}: tag [{tag}] cannot be empty.")
    return value


def _group_unique_blocks(
    blocks: list[tuple[str, str]],
    required_tags: Iterable[str],
    context: str,
    allow_empty_tags: Iterable[str] = (),
) -> dict[str, str]:
    result: dict[str, str] = {}
    allowed_empty = set(allow_empty_tags)
    for tag in required_tags:
        result[tag] = _single_required_block(blocks, tag, context, allow_empty=tag in allowed_empty)

    seen_tags = {name for name, _ in blocks}
    missing = set(required_tags) - seen_tags
    extras = seen_tags - set(required_tags)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise PacketError(f"{context}: missing required tags: {missing_list}.")
    if extras:
        extra_list = ", ".join(sorted(extras))
        raise PacketError(f"{context}: unexpected tags: {extra_list}.")
    return result


def _normalize_positive_number(value: str, field_name: str, zero_pad: bool) -> str:
    stripped = _strip_outer_whitespace(value)
    if not re.fullmatch(r"\d+", stripped):
        raise PacketError(f"{field_name}: expected a positive integer.")
    numeric_value = int(stripped)
    if numeric_value <= 0:
        raise PacketError(f"{field_name}: expected a positive integer.")
    if zero_pad:
        return f"{numeric_value:03d}"
    return str(numeric_value)


def _parse_legacy_packet_text(text: str) -> PacketData:
    top_blocks = _parse_tag_blocks(text, LEGACY_TOP_LEVEL_TAGS, "packet")
    top_values = _group_unique_blocks(
        top_blocks,
        LEGACY_TOP_LEVEL_TAGS,
        "packet",
        allow_empty_tags={"ADVENTURE_TEXT", "COMMENTARY", "STATE", "IMAGES"},
    )

    adventure_blocks = _parse_tag_blocks(top_values["ADVENTURE_TEXT"], {"PARAGRAPH"}, "ADVENTURE_TEXT")
    if not adventure_blocks:
        raise PacketError("ADVENTURE_TEXT: expected at least one [PARAGRAPH] block.")
    adventure_text = []
    for tag, body in adventure_blocks:
        if tag != "PARAGRAPH":
            raise PacketError("ADVENTURE_TEXT: unexpected tag encountered.")
        paragraph = _strip_outer_whitespace(body)
        if not paragraph:
            raise PacketError("ADVENTURE_TEXT: paragraph blocks cannot be empty.")
        adventure_text.append(paragraph)

    commentary_blocks = _parse_tag_blocks(top_values["COMMENTARY"], {"COMMENT"}, "COMMENTARY")
    if not commentary_blocks:
        raise PacketError("COMMENTARY: expected at least one [COMMENT] block.")
    commentary: list[CommentEntry] = []
    for _, body in commentary_blocks:
        comment_blocks = _parse_tag_blocks(body, {"SPEAKER", "CONTENT"}, "COMMENT")
        comment_values = _group_unique_blocks(comment_blocks, {"SPEAKER", "CONTENT"}, "COMMENT")
        commentary.append(CommentEntry(speaker=comment_values["SPEAKER"], content=comment_values["CONTENT"]))

    state_blocks = _parse_tag_blocks(top_values["STATE"], STATE_TAGS.keys(), "STATE")
    state_values = _group_unique_blocks(state_blocks, STATE_TAGS.keys(), "STATE")
    state = {STATE_TAGS[tag]: value for tag, value in state_values.items()}

    image_blocks = _parse_tag_blocks(top_values["IMAGES"], {"IMAGE"}, "IMAGES")
    images: list[ImageEntry] = []
    for _, body in image_blocks:
        parsed_image_blocks = _parse_tag_blocks(body, {"SRC", "ALT", "IMAGE_TITLE", "CAPTION"}, "IMAGE")
        image_values = _group_unique_blocks(parsed_image_blocks, {"SRC", "ALT", "IMAGE_TITLE", "CAPTION"}, "IMAGE")
        images.append(
            ImageEntry(
                src=image_values["SRC"],
                alt=image_values["ALT"],
                title=image_values["IMAGE_TITLE"],
                caption=image_values["CAPTION"],
            )
        )

    segment_number = top_values["SEGMENT_NUMBER"]
    segment_slug = top_values["SEGMENT_SLUG"]
    if not re.fullmatch(r"\d{3}", segment_number):
        raise PacketError("packet: [SEGMENT_NUMBER] must be exactly three digits.")
    if not re.fullmatch(r"segment-\d{3}", segment_slug):
        raise PacketError("packet: [SEGMENT_SLUG] must match the form segment-###.")
    expected_slug = f"segment-{segment_number}"
    if segment_slug != expected_slug:
        raise PacketError(
            f"packet: [SEGMENT_NUMBER] and [SEGMENT_SLUG] disagree. Expected slug '{expected_slug}'."
        )

    return PacketData(
        segment_number=segment_number,
        segment_slug=segment_slug,
        era_slug=top_values["ERA_SLUG"],
        title=top_values["TITLE"],
        location=top_values["LOCATION"],
        tagline=top_values["TAGLINE"],
        adventure_text=adventure_text,
        commentary=commentary,
        summary=top_values["SUMMARY"],
        state=state,
        images=images,
    )


def _split_adventure_paragraphs(text: str) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"(?:\r?\n){2,}", text.strip())
        if paragraph.strip()
    ]
    if not paragraphs:
        raise PacketError("adventure text: expected at least one paragraph.")
    return paragraphs


def _parse_template_commentary(text: str) -> list[CommentEntry]:
    comment_blocks = _parse_tag_blocks(text, {"assistant", "user"}, "commentary")
    if not comment_blocks:
        raise PacketError("commentary: expected at least one [assistant] or [user] block.")

    commentary: list[CommentEntry] = []
    for tag, body in comment_blocks:
        content = _strip_outer_whitespace(body)
        if not content:
            raise PacketError(f"commentary: tag [{tag}] cannot be empty.")
        commentary.append(CommentEntry(speaker=tag.title(), content=content))
    return commentary


def _parse_template_images(text: str) -> list[ImageEntry]:
    image_blocks = _parse_tag_blocks(text, set(TEMPLATE_IMAGE_SEQUENCE), "images")
    if not image_blocks:
        return []

    if len(image_blocks) % len(TEMPLATE_IMAGE_SEQUENCE) != 0:
        raise PacketError("images: expected repeated groups of image title, location, alt text, and caption.")

    images: list[ImageEntry] = []
    for index in range(0, len(image_blocks), len(TEMPLATE_IMAGE_SEQUENCE)):
        group = image_blocks[index : index + len(TEMPLATE_IMAGE_SEQUENCE)]
        tags = tuple(tag for tag, _ in group)
        if tags != TEMPLATE_IMAGE_SEQUENCE:
            expected = ", ".join(f"[{tag}]" for tag in TEMPLATE_IMAGE_SEQUENCE)
            raise PacketError(f"images: expected tag sequence {expected}.")

        values = {tag: _strip_outer_whitespace(body) for tag, body in group}
        for tag, value in values.items():
            if not value:
                raise PacketError(f"images: tag [{tag}] cannot be empty.")

        images.append(
            ImageEntry(
                title=values["image title"],
                src=values["image location"],
                alt=values["image alt text"],
                caption=values["image caption"],
            )
        )
    return images


def _parse_template_state(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise PacketError("state: expected at least the required state lines.")

    state: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            raise PacketError(f"state: expected 'Key: Value' lines, got '{line}'.")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in state:
            raise PacketError(f"state: duplicate state key '{key}'.")
        state[key] = value

    missing = [key for key in TEMPLATE_STATE_KEYS if key not in state]
    if missing:
        raise PacketError(f"state: missing required keys: {', '.join(missing)}.")
    for key in TEMPLATE_STATE_KEYS:
        if not state[key]:
            raise PacketError(f"state: key '{key}' cannot be empty.")

    return state


def _parse_template_packet_text(text: str) -> PacketData:
    top_blocks = _parse_tag_blocks(text, TEMPLATE_TOP_LEVEL_TAGS, "template packet")
    top_values = _group_unique_blocks(
        top_blocks,
        TEMPLATE_TOP_LEVEL_TAGS,
        "template packet",
        allow_empty_tags={"images"},
    )

    segment_number = _normalize_positive_number(top_values["segment number"], "segment number", zero_pad=True)
    era_reference = _normalize_positive_number(top_values["era number"], "era number", zero_pad=False)
    segment_slug = f"segment-{segment_number}"

    return PacketData(
        segment_number=segment_number,
        segment_slug=segment_slug,
        era_slug=era_reference,
        title=top_values["segment title"],
        location=top_values["location"],
        tagline=top_values["tagline"],
        adventure_text=_split_adventure_paragraphs(top_values["adventure text"]),
        commentary=_parse_template_commentary(top_values["commentary"]),
        summary=top_values["summary"],
        state=_parse_template_state(top_values["state"]),
        images=_parse_template_images(top_values["images"]),
    )


def parse_packet_text(text: str) -> PacketData:
    stripped = text.lstrip()
    if stripped.startswith("[era number]"):
        return _parse_template_packet_text(text)
    return _parse_legacy_packet_text(text)


def _to_roman(number: int) -> str:
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    result = []
    remainder = number
    for value, symbol in numerals:
        while remainder >= value:
            remainder -= value
            result.append(symbol)
    return "".join(result)


def _number_word(number: int) -> str | None:
    return {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
    }.get(number)


def _resolve_era_slug(era_reference: str, chronicle: dict[str, object]) -> str:
    eras = chronicle.get("eras", [])
    exact_slug_matches = [
        era.get("slug")
        for era in eras
        if isinstance(era, dict) and era.get("slug") == era_reference
    ]
    if exact_slug_matches:
        return exact_slug_matches[0]

    if not era_reference.isdigit():
        raise PacketError(f"ERA reference does not exist in chronicle_data.json: {era_reference}")

    era_number = int(era_reference)
    roman = _to_roman(era_number).lower()
    word = _number_word(era_number)
    matches: list[str] = []

    for era in eras:
        if not isinstance(era, dict):
            continue
        slug = str(era.get("slug", ""))
        label = str(era.get("label", "")).strip().lower()
        title = str(era.get("title", "")).strip().lower()

        if label == f"era {roman}" or title.startswith(f"era {roman}"):
            matches.append(slug)
            continue
        if label == f"era {era_number}" or title.startswith(f"era {era_number}"):
            matches.append(slug)
            continue
        if word and slug == f"era-{word}":
            matches.append(slug)

    unique_matches = list(dict.fromkeys(matches))
    if len(unique_matches) == 1:
        return unique_matches[0]
    if len(unique_matches) > 1:
        raise PacketError(f"Era number {era_reference} matched multiple eras: {', '.join(unique_matches)}")
    raise PacketError(f"Era number {era_reference} does not match any era in chronicle_data.json")


def load_chronicle(chronicle_path: Path) -> dict[str, object]:
    try:
        with chronicle_path.open("r", encoding="utf-8") as handle:
            chronicle = json.load(handle)
    except FileNotFoundError as exc:
        raise PacketError(f"Chronicle file not found: {chronicle_path}") from exc
    except json.JSONDecodeError as exc:
        raise PacketError(f"Chronicle JSON is invalid: {exc}") from exc

    if not isinstance(chronicle, dict):
        raise PacketError("Chronicle root must be a JSON object.")
    eras = chronicle.get("eras")
    if not isinstance(eras, list):
        raise PacketError("Chronicle JSON must contain an 'eras' array.")
    return chronicle


def _validate_image_paths(images: list[ImageEntry], project_root: Path) -> None:
    for image in images:
        image_path = Path(image.src)
        if not image_path.is_absolute():
            image_path = project_root / image_path
        if not image_path.exists():
            raise PacketError(f"Image path does not exist: {image.src}")


def validate_against_chronicle(packet: PacketData, chronicle: dict[str, object], project_root: Path) -> str:
    eras = chronicle.get("eras", [])
    resolved_era_slug = _resolve_era_slug(packet.era_slug, chronicle)

    for era in eras:
        if not isinstance(era, dict):
            continue
        for segment in era.get("segments", []):
            if not isinstance(segment, dict):
                continue
            if segment.get("number") == packet.segment_number:
                raise PacketError(f"SEGMENT_NUMBER already exists: {packet.segment_number}")
            if segment.get("slug") == packet.segment_slug:
                raise PacketError(f"SEGMENT_SLUG already exists: {packet.segment_slug}")

    _validate_image_paths(packet.images, project_root)
    return resolved_era_slug


def build_import_result(packet_path: Path, chronicle_path: Path, project_root: Path) -> ImportResult:
    text = packet_path.read_text(encoding="utf-8-sig")
    packet = parse_packet_text(text)
    chronicle = load_chronicle(chronicle_path)
    resolved_era_slug = validate_against_chronicle(packet, chronicle, project_root)
    packet = replace(packet, era_slug=resolved_era_slug)
    return ImportResult(packet=packet, segment_object=packet.to_segment_object(), chronicle_path=chronicle_path)


def create_backup(chronicle_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"{chronicle_path.stem}.{timestamp}{chronicle_path.suffix}"
    shutil.copy2(chronicle_path, backup_path)
    return backup_path


def append_segment(chronicle_path: Path, era_slug: str, segment_object: dict[str, object]) -> None:
    chronicle = load_chronicle(chronicle_path)
    eras = chronicle["eras"]
    for era in eras:
        if isinstance(era, dict) and era.get("slug") == era_slug:
            segments = era.get("segments")
            if not isinstance(segments, list):
                raise PacketError(f"Era '{era_slug}' does not have a valid segments array.")
            segments.append(segment_object)
            break
    else:
        raise PacketError(f"ERA_SLUG does not exist in chronicle_data.json: {era_slug}")

    chronicle_path.write_text(
        json.dumps(chronicle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_validate(packet_path: Path, chronicle_path: Path, project_root: Path) -> ImportResult:
    return build_import_result(packet_path, chronicle_path, project_root)


def run_import(
    packet_path: Path,
    chronicle_path: Path,
    project_root: Path,
    backup_dir: Path,
    dry_run: bool,
) -> ImportResult:
    result = build_import_result(packet_path, chronicle_path, project_root)
    if dry_run:
        return result

    backup_path = create_backup(chronicle_path, backup_dir)
    append_segment(chronicle_path, result.packet.era_slug, result.segment_object)
    return ImportResult(
        packet=result.packet,
        segment_object=result.segment_object,
        chronicle_path=chronicle_path,
        backup_path=backup_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and import reviewed chronicle text files into chronicle_data.json."
    )
    parser.add_argument(
        "--chronicle",
        default=str(DEFAULT_CHRONICLE_PATH),
        help="Path to chronicle_data.json. Defaults to the project chronicle.",
    )
    parser.add_argument(
        "--project-root",
        default=str(PROJECT_ROOT),
        help="Project root used for relative image paths. Defaults to the current project.",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(DEFAULT_BACKUP_DIR),
        help="Directory where chronicle backups are written during import.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a reviewed chronicle text file without writing anything.")
    validate_parser.add_argument("packet", help="Path to the reviewed chronicle text file.")

    import_parser = subparsers.add_parser("import", help="Validate and import a reviewed chronicle text file.")
    import_parser.add_argument("packet", help="Path to the reviewed chronicle text file.")
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the JSON object that would be appended without writing files.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    chronicle_path = Path(args.chronicle)
    project_root = Path(args.project_root)
    backup_dir = Path(args.backup_dir)
    packet_path = Path(args.packet)

    try:
        if args.command == "validate":
            result = run_validate(packet_path, chronicle_path, project_root)
            print(
                f"Valid packet: {packet_path}\n"
                f"Segment: {result.packet.segment_number} ({result.packet.segment_slug})\n"
                f"Era: {result.packet.era_slug}"
            )
            return 0

        result = run_import(packet_path, chronicle_path, project_root, backup_dir, args.dry_run)
        if args.dry_run:
            print(json.dumps(result.segment_object, indent=2, ensure_ascii=False))
            return 0

        print(
            f"Imported segment {result.packet.segment_number} into era '{result.packet.era_slug}'.\n"
            f"Backup created: {result.backup_path}"
        )
        return 0
    except PacketError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
