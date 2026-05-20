function setExpanded(button, expanded) {
  const targetId = button.getAttribute('data-target');
  if (!targetId) return;
  const target = document.getElementById(targetId);
  if (!target) return;
  button.setAttribute('aria-expanded', String(expanded));
  target.hidden = !expanded;
}

function toggleFromButton(button) {
  const expanded = button.getAttribute('aria-expanded') === 'true';
  setExpanded(button, !expanded);
}

function bindCollapsibleButtons() {
  document.querySelectorAll('.era-header, .segment-header, .collapsible-trigger').forEach((button) => {
    button.addEventListener('click', () => {
      toggleFromButton(button);
      if (button.classList.contains('collapsible-trigger')) {
        syncTocArrows();
      }
    });
  });
}

function buildToc() {
  const toc = document.getElementById('toc');
  toc.textContent = '';

  document.querySelectorAll('.era').forEach((era) => {
    const eraId = era.id;
    const eraTitle = era.getAttribute('data-era-title') || eraId;
    const tocEraId = `toc-${eraId}-segments`;

    const eraLi = document.createElement('li');

    const eraHeader = document.createElement('div');
    eraHeader.className = 'toc-era-header';

    const eraToggle = document.createElement('button');
    eraToggle.type = 'button';
    eraToggle.className = 'collapsible-trigger';
    eraToggle.textContent = '▸';
    eraToggle.setAttribute('aria-label', `Toggle ${eraTitle} in table of contents`);
    eraToggle.setAttribute('aria-expanded', 'false');
    eraToggle.setAttribute('data-target', tocEraId);

    const eraLink = document.createElement('a');
    eraLink.className = 'toc-link';
    eraLink.href = `#${eraId}`;
    eraLink.textContent = eraTitle;

    eraHeader.appendChild(eraToggle);
    eraHeader.appendChild(eraLink);

    const segmentsList = document.createElement('ul');
    segmentsList.id = tocEraId;
    segmentsList.className = 'toc-segments';
    segmentsList.hidden = true;

    era.querySelectorAll('.segment').forEach((segment) => {
      const number = segment.getAttribute('data-segment-number') || '???';
      const title = segment.getAttribute('data-segment-title') || segment.id;
      const item = document.createElement('li');
      const link = document.createElement('a');
      link.className = 'toc-link';
      link.href = `#${segment.id}`;
      link.textContent = `Segment ${number} · ${title}`;
      link.addEventListener('click', () => {
        const eraHeaderButton = era.querySelector('.era-header');
        const segmentHeaderButton = segment.querySelector('.segment-header');
        if (eraHeaderButton) setExpanded(eraHeaderButton, true);
        if (segmentHeaderButton) setExpanded(segmentHeaderButton, true);
      });
      item.appendChild(link);
      segmentsList.appendChild(item);
    });

    eraLi.appendChild(eraHeader);
    eraLi.appendChild(segmentsList);
    toc.appendChild(eraLi);
  });
}

function syncTocArrows() {
  document.querySelectorAll('.collapsible-trigger').forEach((button) => {
    button.textContent = button.getAttribute('aria-expanded') === 'true' ? '▾' : '▸';
  });
}

function expandCollapseAll(expand) {
  document.querySelectorAll('.era-header, .segment-header, .collapsible-trigger').forEach((button) => {
    setExpanded(button, expand);
  });
  syncTocArrows();
}

function slugify(value, fallback = 'item') {
  return String(value || fallback)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || fallback;
}

function createSectionWithHeading(className, headingText) {
  const section = document.createElement('section');
  section.className = className;
  const heading = document.createElement('h5');
  heading.textContent = headingText;
  section.appendChild(heading);
  return section;
}

function renderSegment(segment, eraLabel, eraSlug, segmentIndex) {
  const segmentSlug = segment.slug || `segment-${String(segment.number || segmentIndex + 1).padStart(3, '0')}`;

  const article = document.createElement('article');
  article.className = 'segment';
  article.id = segmentSlug;
  article.setAttribute('data-segment-number', String(segment.number || '???'));
  article.setAttribute('data-segment-title', segment.title || segmentSlug);

  const headerButton = document.createElement('button');
  headerButton.className = 'segment-header';
  headerButton.type = 'button';
  headerButton.setAttribute('data-target', `${segmentSlug}-content`);
  headerButton.setAttribute('aria-expanded', 'false');

  const kicker = document.createElement('div');
  kicker.className = 'segment-kicker';
  [
    `Segment ${String(segment.number || segmentIndex + 1).padStart(3, '0')}`,
    eraLabel,
    segment.location || 'Location TBD'
  ].forEach((value) => {
    const span = document.createElement('span');
    span.textContent = value;
    kicker.appendChild(span);
  });

  const title = document.createElement('h4');
  title.textContent = segment.title || `Untitled Segment ${segmentIndex + 1}`;

  const tagline = document.createElement('p');
  tagline.textContent = segment.tagline || '[tagline]';

  headerButton.append(kicker, title, tagline);

  const body = document.createElement('div');
  body.className = 'segment-body';
  body.id = `${segmentSlug}-content`;
  body.hidden = true;

  const textSection = createSectionWithHeading('text-block', 'Adventure Segment');
  (segment.adventureText || []).forEach((paragraphText) => {
    const p = document.createElement('p');
    p.textContent = paragraphText;
    textSection.appendChild(p);
  });

  const imagesSection = createSectionWithHeading('images', 'Images');
  if (!segment.images || !segment.images.length) {
    const noImages = document.createElement('p');
    noImages.textContent = 'No images recorded for this segment.';
    imagesSection.appendChild(noImages);
  } else {
    segment.images.forEach((image) => {
      const figure = document.createElement('figure');
      figure.className = 'image-entry';

      const img = document.createElement('img');
      img.src = image.src;
      img.alt = image.alt || image.title || 'Segment image';

      const figCaption = document.createElement('figcaption');
      figCaption.className = 'image-meta';

      const imageTitle = document.createElement('div');
      imageTitle.className = 'image-title';
      imageTitle.textContent = image.title || 'Untitled image';

      const imageCaption = document.createElement('p');
      imageCaption.className = 'image-caption';
      imageCaption.textContent = image.caption || '';

      figCaption.append(imageTitle, imageCaption);
      figure.append(img, figCaption);
      imagesSection.appendChild(figure);
    });
  }

  const commentarySection = createSectionWithHeading('commentary', 'Commentary');
  const commentaryList = document.createElement('div');
  commentaryList.className = 'commentary-list';
  (segment.commentary || []).forEach((entry) => {
    const entryArticle = document.createElement('article');
    entryArticle.className = 'commentary-entry';

    const speaker = document.createElement('p');
    speaker.className = 'commentary-speaker';
    speaker.textContent = entry.speaker || 'Unknown';

    const content = document.createElement('p');
    content.className = 'commentary-content';
    content.textContent = entry.content || '';

    entryArticle.append(speaker, content);
    commentaryList.appendChild(entryArticle);
  });
  commentarySection.appendChild(commentaryList);

  const summarySection = createSectionWithHeading('summary', 'Summary');
  const summaryText = document.createElement('p');
  summaryText.textContent = segment.summary || '';
  summarySection.appendChild(summaryText);

  const stateSection = createSectionWithHeading('state', 'State');
  const stateGrid = document.createElement('dl');
  stateGrid.className = 'state-grid';
  Object.entries(segment.state || {}).forEach(([key, value]) => {
    const item = document.createElement('div');
    item.className = 'state-item';

    const dt = document.createElement('dt');
    dt.textContent = key;
    const dd = document.createElement('dd');
    dd.textContent = value;

    item.append(dt, dd);
    stateGrid.appendChild(item);
  });
  stateSection.appendChild(stateGrid);

  body.append(textSection, imagesSection, commentarySection, summarySection, stateSection);
  article.append(headerButton, body);
  return article;
}

function renderEra(era, eraIndex) {
  const eraSlug = era.slug || `era-${slugify(era.title, `era-${eraIndex + 1}`)}`;

  const section = document.createElement('section');
  section.className = 'era';
  section.id = eraSlug;
  section.setAttribute('data-era-title', era.title || `Era ${eraIndex + 1}`);

  const headerButton = document.createElement('button');
  headerButton.className = 'era-header';
  headerButton.type = 'button';
  headerButton.setAttribute('data-target', `${eraSlug}-content`);
  headerButton.setAttribute('aria-expanded', 'false');

  const strong = document.createElement('strong');
  strong.textContent = era.title || `Era ${eraIndex + 1}`;
  const span = document.createElement('span');
  span.textContent = era.subtitle || '';
  headerButton.append(strong, span);

  const content = document.createElement('div');
  content.className = 'era-content';
  content.id = `${eraSlug}-content`;
  content.hidden = true;

  (era.segments || []).forEach((segment, segmentIndex) => {
    content.appendChild(renderSegment(segment, era.label || era.title || `Era ${eraIndex + 1}`, eraSlug, segmentIndex));
  });

  section.append(headerButton, content);
  return section;
}

async function loadChronicle() {
  const response = await fetch('./chronicle_data.json');
  if (!response.ok) {
    throw new Error(`Unable to load chronicle data (${response.status})`);
  }

  const data = await response.json();

  document.getElementById('sidebar-title').textContent = data.sidebar.title;
  document.getElementById('sidebar-subtitle').textContent = data.sidebar.subtitle;

  document.getElementById('doc-eyebrow').textContent = data.document.eyebrow;
  document.getElementById('doc-title').textContent = data.document.title;
  document.getElementById('doc-description').textContent = data.document.description;

  const erasRoot = document.getElementById('eras-root');
  erasRoot.textContent = '';
  (data.eras || []).forEach((era, index) => {
    erasRoot.appendChild(renderEra(era, index));
  });
}

async function init() {
  try {
    await loadChronicle();

    buildToc();
    bindCollapsibleButtons();
    syncTocArrows();

    document.getElementById('expand-all').addEventListener('click', () => expandCollapseAll(true));
    document.getElementById('collapse-all').addEventListener('click', () => expandCollapseAll(false));
  } catch (error) {
    console.error(error);
    const erasRoot = document.getElementById('eras-root');
    erasRoot.innerHTML = '<p>Could not load chronicle data. Please run this page through a local web server.</p>';
  }
}

init();
