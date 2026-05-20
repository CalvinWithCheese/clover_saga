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
  document.querySelectorAll('.era-header, .segment-header, .prologue-header, .collapsible-trigger').forEach((button) => {
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

  const prologue = document.getElementById('prologue');
  if (prologue) {
    const prologueTitle = prologue.getAttribute('data-prologue-title') || 'Prologue';
    const prologueLi = document.createElement('li');
    const prologueLink = document.createElement('a');
    prologueLink.className = 'toc-link';
    prologueLink.href = '#prologue';
    prologueLink.textContent = prologueTitle;
    prologueLi.appendChild(prologueLink);
    toc.appendChild(prologueLi);
  }

  document.querySelectorAll('.era').forEach((era) => {
    const eraId = era.id;
    const eraTitle = era.getAttribute('data-era-title') || eraId;
    const tocEraId = `toc-${eraId}-segments`;
    const segmentsRoot = document.getElementById(`${eraId}-content`);

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
    segmentsList.className = 'toc-segment-list';
    segmentsList.hidden = true;

    segmentsRoot?.querySelectorAll('.segment').forEach((segment) => {
      const segmentLi = document.createElement('li');
      const segmentLink = document.createElement('a');
      segmentLink.className = 'toc-link';
      segmentLink.href = `#${segment.id}`;
      segmentLink.textContent = segment.getAttribute('data-segment-title') || segment.id;
      segmentLi.appendChild(segmentLink);
      segmentsList.appendChild(segmentLi);
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
  document.querySelectorAll('.era-header, .segment-header, .prologue-header, .collapsible-trigger').forEach((button) => {
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

function renderSegment(segment, eraLabel, segmentIndex, options = {}) {
  const segmentSlug = segment.slug || `segment-${String(segment.number || segmentIndex + 1).padStart(3, '0')}`;

  const article = document.createElement('article');
  article.className = 'segment';
  if (options.additionalClass) {
    article.classList.add(options.additionalClass);
  }
  article.id = segmentSlug;
  article.setAttribute('data-segment-number', String(segment.number || '???'));
  article.setAttribute('data-segment-title', segment.title || segmentSlug);

  const headerButton = document.createElement('button');
  headerButton.className = 'segment-header';
  if (options.headerClass) {
    headerButton.classList.add(options.headerClass);
  }
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

  article.append(headerButton, body);
  return article;
}

function renderPrologue(prologue) {
  const wrapper = document.createElement('section');
  wrapper.className = 'prologue-card';
  wrapper.id = 'prologue';
  wrapper.setAttribute('data-prologue-title', prologue.label || 'Prologue');

  const heading = document.createElement('header');
  heading.className = 'prologue-heading';

  const eyebrow = document.createElement('p');
  eyebrow.className = 'prologue-eyebrow';
  eyebrow.textContent = prologue.label || 'Prologue';

  const title = document.createElement('h3');
  title.textContent = prologue.title || 'Untitled Prologue';

  const subtitle = document.createElement('p');
  subtitle.className = 'prologue-subtitle';
  subtitle.textContent = prologue.subtitle || '';

  heading.append(eyebrow, title, subtitle);

  const prologueSegment = {
    ...prologue,
    number: prologue.number || '000',
    title: prologue.title || 'Untitled Prologue',
    location: prologue.location || 'Location TBD',
    tagline: prologue.tagline || prologue.subtitle || '[tagline]'
  };

  wrapper.append(
    heading,
    renderSegment(prologueSegment, prologue.label || 'Prologue', 0, {
      additionalClass: 'prologue-segment',
      headerClass: 'prologue-header'
    })
  );

  return wrapper;
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
    content.appendChild(renderSegment(segment, era.label || era.title || `Era ${eraIndex + 1}`, segmentIndex));
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
  if (data.prologue) {
    erasRoot.appendChild(renderPrologue(data.prologue));
  }

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