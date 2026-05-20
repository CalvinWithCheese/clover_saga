from __future__ import annotations

import json
import shutil
import unittest
import uuid
from pathlib import Path

from tools import chronicle_import


class ChronicleImportTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace_root = Path(__file__).resolve().parents[1]
        self.root = workspace_root / "tests" / "_tmp" / f"case-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True)
        (self.root / "images").mkdir()
        (self.root / "workflow" / "backups").mkdir(parents=True)

        self.chronicle_path = self.root / "chronicle_data.json"
        self.packet_path = self.root / "packet.txt"
        self.backup_dir = self.root / "workflow" / "backups"

        chronicle = {
            "sidebar": {"title": "Clover Stonefield", "subtitle": "Adventure Chronicle"},
            "document": {"eyebrow": "Chronicle Document", "title": "Saga", "description": "Test chronicle"},
            "prologue": {
                "slug": "prologue-segment-000",
                "number": "000",
                "label": "Prologue",
                "title": "Start",
                "subtitle": "Beginning",
                "location": "Rorikstead",
                "tagline": "Before the road.",
                "adventureText": ["Intro paragraph."],
                "images": [],
            },
            "eras": [
                {
                    "slug": "era-one",
                    "label": "Era I",
                    "title": "Era I",
                    "subtitle": "Road",
                    "segments": [
                        {
                            "slug": "segment-001",
                            "number": "001",
                            "title": "Dust on Her Boots",
                            "location": "Road",
                            "tagline": "Sample",
                            "adventureText": ["Existing segment."],
                            "images": [],
                            "commentary": [{"speaker": "Assistant", "content": "Existing comment."}],
                            "summary": "Existing summary.",
                            "state": {
                                "Location": "Road",
                                "Weapons": "Iron greatsword",
                                "Gear": "Travel clothes",
                                "Status": "Fine",
                                "Special items": "Coin pouch",
                                "Objective": "Reach Whiterun",
                            },
                        }
                    ],
                },
                {
                    "slug": "era-two",
                    "label": "Era II",
                    "title": "Era II",
                    "subtitle": "Whiterun",
                    "segments": [],
                },
            ],
        }
        self.chronicle_path.write_text(json.dumps(chronicle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root)

    def write_packet(self, text: str) -> Path:
        self.packet_path.write_text(text, encoding="utf-8")
        return self.packet_path

    def packet_text(self, images_block: str = "") -> str:
        return f"""[SEGMENT_NUMBER]005[/SEGMENT_NUMBER]
[SEGMENT_SLUG]segment-005[/SEGMENT_SLUG]
[ERA_SLUG]era-two[/ERA_SLUG]
[TITLE]The Next Trial[/TITLE]
[LOCATION]Whiterun[/LOCATION]
[TAGLINE]Clover steps forward.[/TAGLINE]

[ADVENTURE_TEXT]
[PARAGRAPH]First paragraph.[/PARAGRAPH]
[PARAGRAPH]Second paragraph.[/PARAGRAPH]
[/ADVENTURE_TEXT]

[COMMENTARY]
[COMMENT]
[SPEAKER]Assistant[/SPEAKER]
[CONTENT]Commentary text.[/CONTENT]
[/COMMENT]
[COMMENT]
[SPEAKER]User[/SPEAKER]
[CONTENT]Response text.[/CONTENT]
[/COMMENT]
[/COMMENTARY]

[SUMMARY]A short summary.[/SUMMARY]

[STATE]
[STATE_LOCATION]Whiterun[/STATE_LOCATION]
[STATE_WEAPONS]Iron greatsword[/STATE_WEAPONS]
[STATE_GEAR]Hide armor[/STATE_GEAR]
[STATE_STATUS]Confident[/STATE_STATUS]
[STATE_SPECIAL_ITEMS]Coin pouch[/STATE_SPECIAL_ITEMS]
[STATE_OBJECTIVE]Speak to the Companions[/STATE_OBJECTIVE]
[/STATE]

[IMAGES]
{images_block}[/IMAGES]
"""

    def template_packet_text(self, images_block: str = "") -> str:
        return f"""[era number]
2
[/era number]

[segment number]
5
[/segment number]

[segment title]
The Next Trial
[/segment title]

[location]
Whiterun
[/location]

[tagline]
Clover steps forward.
[/tagline]

[adventure text]
First paragraph.

Second paragraph.
[/adventure text]

[images]
{images_block}[/images]

[commentary]
[assistant]Commentary text.[/assistant]
[user]Response text.[/user]
[/commentary]

[summary]
A short summary.
[/summary]

[state]
Location: Whiterun
Weapons: Iron greatsword
Gear: Hide armor
Objective: Speak to the Companions
[/state]
"""

    def test_validate_packet_without_images(self) -> None:
        packet = self.write_packet(self.packet_text())
        result = chronicle_import.run_validate(packet, self.chronicle_path, self.root)
        self.assertEqual(result.packet.segment_number, "005")
        self.assertEqual(result.packet.era_slug, "era-two")
        self.assertEqual(result.segment_object["images"], [])

    def test_validate_template_packet_without_images(self) -> None:
        packet = self.write_packet(self.template_packet_text())
        result = chronicle_import.run_validate(packet, self.chronicle_path, self.root)
        self.assertEqual(result.packet.segment_number, "005")
        self.assertEqual(result.packet.segment_slug, "segment-005")
        self.assertEqual(result.packet.era_slug, "era-two")
        self.assertEqual(result.segment_object["images"], [])
        self.assertEqual(result.segment_object["state"]["Objective"], "Speak to the Companions")

    def test_validate_packet_with_multiple_images(self) -> None:
        (self.root / "images" / "scene-one.png").write_text("not-a-real-image", encoding="utf-8")
        (self.root / "images" / "scene-two.png").write_text("not-a-real-image", encoding="utf-8")
        images_block = """[IMAGE]
[SRC]images/scene-one.png[/SRC]
[ALT]Scene one[/ALT]
[IMAGE_TITLE]Scene One[/IMAGE_TITLE]
[CAPTION]First caption.[/CAPTION]
[/IMAGE]
[IMAGE]
[SRC]images/scene-two.png[/SRC]
[ALT]Scene two[/ALT]
[IMAGE_TITLE]Scene Two[/IMAGE_TITLE]
[CAPTION]Second caption.[/CAPTION]
[/IMAGE]
"""
        packet = self.write_packet(self.packet_text(images_block=images_block))
        result = chronicle_import.run_validate(packet, self.chronicle_path, self.root)
        self.assertEqual(len(result.segment_object["images"]), 2)

    def test_validate_template_packet_with_multiple_images(self) -> None:
        (self.root / "images" / "scene-one.png").write_text("not-a-real-image", encoding="utf-8")
        (self.root / "images" / "scene-two.png").write_text("not-a-real-image", encoding="utf-8")
        images_block = """[image title]Scene One[/image title]
[image location]images/scene-one.png[/image location]
[image alt text]Scene one[/image alt text]
[image caption]First caption.[/image caption]
[image title]Scene Two[/image title]
[image location]images/scene-two.png[/image location]
[image alt text]Scene two[/image alt text]
[image caption]Second caption.[/image caption]
"""
        packet = self.write_packet(self.template_packet_text(images_block=images_block))
        result = chronicle_import.run_validate(packet, self.chronicle_path, self.root)
        self.assertEqual(len(result.segment_object["images"]), 2)

    def test_missing_state_field_fails(self) -> None:
        broken_packet = self.packet_text().replace(
            "[STATE_OBJECTIVE]Speak to the Companions[/STATE_OBJECTIVE]\n", ""
        )
        packet = self.write_packet(broken_packet)
        with self.assertRaises(chronicle_import.PacketError):
            chronicle_import.run_validate(packet, self.chronicle_path, self.root)

    def test_template_missing_state_field_fails(self) -> None:
        broken_packet = self.template_packet_text().replace("Objective: Speak to the Companions\n", "")
        packet = self.write_packet(broken_packet)
        with self.assertRaises(chronicle_import.PacketError):
            chronicle_import.run_validate(packet, self.chronicle_path, self.root)

    def test_nonexistent_image_path_fails(self) -> None:
        images_block = """[IMAGE]
[SRC]images/missing.png[/SRC]
[ALT]Missing image[/ALT]
[IMAGE_TITLE]Missing[/IMAGE_TITLE]
[CAPTION]This should fail.[/CAPTION]
[/IMAGE]
"""
        packet = self.write_packet(self.packet_text(images_block=images_block))
        with self.assertRaises(chronicle_import.PacketError):
            chronicle_import.run_validate(packet, self.chronicle_path, self.root)

    def test_template_import_creates_backup_and_appends(self) -> None:
        packet = self.write_packet(self.template_packet_text())
        result = chronicle_import.run_import(
            packet,
            self.chronicle_path,
            self.root,
            self.backup_dir,
            dry_run=False,
        )
        self.assertIsNotNone(result.backup_path)
        chronicle = json.loads(self.chronicle_path.read_text(encoding="utf-8"))
        era_two = next(era for era in chronicle["eras"] if era["slug"] == "era-two")
        self.assertEqual(len(era_two["segments"]), 1)
        self.assertEqual(era_two["segments"][0]["number"], "005")
        self.assertEqual(era_two["segments"][0]["state"]["Objective"], "Speak to the Companions")

    def test_duplicate_number_fails(self) -> None:
        packet = self.write_packet(self.packet_text().replace("005", "001", 1).replace("segment-005", "segment-001", 1))
        with self.assertRaises(chronicle_import.PacketError):
            chronicle_import.run_validate(packet, self.chronicle_path, self.root)

    def test_dry_run_does_not_write(self) -> None:
        packet = self.write_packet(self.packet_text())
        before = self.chronicle_path.read_text(encoding="utf-8")
        result = chronicle_import.run_import(
            packet,
            self.chronicle_path,
            self.root,
            self.backup_dir,
            dry_run=True,
        )
        after = self.chronicle_path.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result.backup_path, None)

    def test_import_creates_backup_and_appends(self) -> None:
        packet = self.write_packet(self.packet_text())
        result = chronicle_import.run_import(
            packet,
            self.chronicle_path,
            self.root,
            self.backup_dir,
            dry_run=False,
        )
        self.assertIsNotNone(result.backup_path)
        backups = list(self.backup_dir.iterdir())
        self.assertEqual(len(backups), 1)

        chronicle = json.loads(self.chronicle_path.read_text(encoding="utf-8"))
        era_two = next(era for era in chronicle["eras"] if era["slug"] == "era-two")
        self.assertEqual(len(era_two["segments"]), 1)
        self.assertEqual(era_two["segments"][0]["slug"], "segment-005")


if __name__ == "__main__":
    unittest.main()
