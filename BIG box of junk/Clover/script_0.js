(function initSagaPage() {
  const state = {
    eraMap: new Map(),
    segmentMap: new Map()
  };

  const elements = {
    sidebarTitle: document.getElementById('sidebar-title'),
    sidebarSubtitle: document.getElementById('sidebar-subtitle'),
    docEyebrow: document.getElementById('doc-eyebrow'),
    docTitle: document.getElementById('doc-title'),
    docDescription: document.getElementById('doc-description'),
    toc: document.getElementById('toc'),
    erasRoot: document.getElementById('eras-root'),
    expandAll: document.getElementById('expand-all'),
    collapseAll: document.getElementById('collapse-all')
  };

  const setText = (node, value = '') => {
    if (node) {
      node.textContent = value;
    }
  };

  const create = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === 'string') node.textContent = text;
    return node;
  };

  const createLink = (href, text) => {
    const a = document.createElement('a');
    a.href = href;
    a.className = 'toc-link';
    a.textContent = text;
    return a;
  };

  const markCollapsed = (button, collapsed) => {
    if (!button) return;
    button.setAttribute('aria-expanded', String(!collapsed));
    button.dataset.collapsed = String(collapsed);
  };

  const setRegionOpen = (entry, open) => {
    if (!entry?.content || !entry?.button) return;
    entry.content.hidden = !open;
    markCollapsed(entry.button, !open);
  };

  const createSectionBlock = (title, className) => {
    const section = create('section', className);
    const heading = create('h5', '', title);
    section.appendChild(heading);
    return section;
  };

  const buildTextBlock = (segment) => {
    const block = createSectionBlock('Adventure Segment', 'text-block');
    (segment.adventureText || []).forEach((paragraph) => {
      block.appendChild(create('p', '', paragraph));
    });
    return block;
  };

  const buildImagesBlock = (segment) => {
    const images = Array.isArray(segment.images) ? segment.images : [];
    if (images.length === 0) return null;

    const block = createSectionBlock('Images', 'images');
    images.forEach((img) => {
      const entry = create('article', 'image-entry');
      const image = document.createElement('img');
      image.src = img.src || '';
      image.alt = img.alt || img.title || 'Chronicle image';
      image.loading = 'lazy';
      entry.appendChild(image);

      const meta = create('div', 'image-meta');
      meta.appendChild(create('p', 'image-title', img.title || 'Untitled image'));
      if (img.caption) {
        meta.appendChild(create('p', 'image-caption', img.caption));
      }
      entry.appendChild(meta);
      block.appendChild(entry);
    });

    return block;
  };

  const buildCommentaryBlock = (segment) => {
    const commentary = Array.isArray(segment.commentary) ? segment.commentary : [];
    if (commentary.length === 0) return null;

    const block = createSectionBlock('Commentary', 'commentary');
    const list = create('div', 'commentary-list');

    commentary.forEach((entry) => {
      const item = create('article', 'commentary-entry');
      item.appendChild(create('p', 'commentary-speaker', entry.speaker || 'Speaker'));
      item.appendChild(create('p', 'commentary-content', entry.content || ''));
      list.appendChild(item);
    });

    block.appendChild(list);
    return block;
  };

  const buildSummaryBlock = (segment) => {
    if (!segment.summary) return null;
    const block = createSectionBlock('Summary', 'summary');
    block.appendChild(create('p', '', segment.summary));
    return block;
  };

  const buildStateBlock = (segment) => {
    const data = segment.state;
    if (!data || typeof data !== 'object') return null;

    const block = createSectionBlock('State', 'state');
    const grid = create('dl', 'state-grid');

    Object.entries(data).forEach(([key, value]) => {
      const item = create('div', 'state-item');
      item.appendChild(create('dt', '', key));
      item.appendChild(create('dd', '', String(value ?? '')));
      grid.appendChild(item);
    });

    block.appendChild(grid);
    return block;
  };

  const buildSegment = (segment, options = {}) => {
    const isPrologue = Boolean(options.isPrologue);
    const wrapper = create('article', `segment${isPrologue ? ' prologue-segment' : ''}`);

    const segmentSlug = segment.slug || `segment-${segment.number || 'x'}`;
    const segmentId = segmentSlug;
    wrapper.id = segmentId;

    const headerButton = create('button', `segment-header${isPrologue ? ' prologue-header' : ''}`);
    headerButton.type = 'button';

    const kicker = create('p', 'segment-kicker');
    kicker.append(
      create('span', '', `Segment ${segment.number || '?'}`),
      create('span', '', segment.location || 'Unknown location')
    );
    headerButton.appendChild(kicker);

    headerButton.appendChild(create('h4', '', segment.title || 'Untitled segment'));
    headerButton.appendChild(create('p', '', segment.tagline || ''));

    const body = create('div', 'segment-body');
    body.appendChild(buildTextBlock(segment));

    [
      buildImagesBlock(segment),
      buildCommentaryBlock(segment),
      buildSummaryBlock(segment),
      buildStateBlock(segment)
    ].forEach((node) => {
      if (node) body.appendChild(node);
    });

    wrapper.appendChild(headerButton);
    wrapper.appendChild(body);

    const segmentEntry = { button: headerButton, content: body, id: segmentId };
    state.segmentMap.set(segmentId, segmentEntry);
    setRegionOpen(segmentEntry, true);

    headerButton.addEventListener('click', () => {
      const currentlyOpen = !body.hidden;
      setRegionOpen(segmentEntry, !currentlyOpen);
    });

    return wrapper;
  };

  const buildEra = (era) => {
    const eraSlug = era.slug || `era-${Math.random().toString(36).slice(2, 8)}`;
    const eraArticle = create('section', 'era');
    eraArticle.id = eraSlug;

    const header = create('button', 'era-header');
    header.type = 'button';
    header.appendChild(create('strong', '', era.title || era.label || 'Untitled era'));
    header.appendChild(create('span', '', era.subtitle || ''));

    const content = create('div', 'era-content');

    (era.segments || []).forEach((segment) => {
      content.appendChild(buildSegment(segment));
    });

    eraArticle.appendChild(header);
    eraArticle.appendChild(content);

    const eraEntry = { button: header, content, id: eraSlug };
    state.eraMap.set(eraSlug, eraEntry);
    setRegionOpen(eraEntry, true);

    header.addEventListener('click', () => {
      const currentlyOpen = !content.hidden;
      setRegionOpen(eraEntry, !currentlyOpen);
    });

    return eraArticle;
  };

  const buildPrologue = (prologue) => {
    if (!prologue || !Array.isArray(prologue.segments) || prologue.segments.length === 0) {
      return null;
    }

    const card = create('section', 'prologue-card');
    card.id = prologue.slug || 'prologue';

    const heading = create('header', 'prologue-heading');
    heading.appendChild(create('p', 'prologue-eyebrow', prologue.label || 'Prologue'));
    heading.appendChild(create('h3', '', prologue.title || 'Prologue'));
    if (prologue.subtitle) {
      heading.appendChild(create('p', 'prologue-subtitle', prologue.subtitle));
    }

    card.appendChild(heading);

    prologue.segments.forEach((segment) => {
      card.appendChild(buildSegment(segment, { isPrologue: true }));
    });

    return card;
  };

  const buildToc = (data) => {
    elements.toc.innerHTML = '';

    if (data.prologue?.segments?.length) {
      const item = create('li');
      item.appendChild(createLink(`#${data.prologue.slug || 'prologue'}`, data.prologue.title || 'Prologue'));
      const segmentList = create('ul', 'toc-segments');
      data.prologue.segments.forEach((segment) => {
        segmentList.appendChild(create('li')).appendChild(
          createLink(`#${segment.slug || ''}`, `Segment ${segment.number || '?'} · ${segment.title || 'Untitled'}`)
        );
      });
      item.appendChild(segmentList);
      elements.toc.appendChild(item);
    }

    (data.eras || []).forEach((era) => {
      const item = create('li');
      const eraHeader = create('div', 'toc-era-header');
      eraHeader.appendChild(createLink(`#${era.slug || ''}`, era.title || era.label || 'Untitled era'));
      item.appendChild(eraHeader);

      const segments = Array.isArray(era.segments) ? era.segments : [];
      if (segments.length) {
        const segList = create('ul', 'toc-segments');
        segments.forEach((segment) => {
          const segItem = create('li');
          segItem.appendChild(
            createLink(`#${segment.slug || ''}`, `Segment ${segment.number || '?'} · ${segment.title || 'Untitled'}`)
          );
          segList.appendChild(segItem);
        });
        item.appendChild(segList);
      }

      elements.toc.appendChild(item);
    });
  };

  const setAllOpen = (open) => {
    state.eraMap.forEach((entry) => setRegionOpen(entry, open));
    state.segmentMap.forEach((entry) => setRegionOpen(entry, open));
  };

  const render = (data) => {
    setText(elements.sidebarTitle, data.sidebar?.title || 'Clover Stonefield');
    setText(elements.sidebarSubtitle, data.sidebar?.subtitle || 'Adventure Chronicle');

    setText(elements.docEyebrow, data.document?.eyebrow || 'Chronicle Document');
    setText(elements.docTitle, data.document?.title || 'The Saga of Clover Stonefield');
    setText(elements.docDescription, data.document?.description || '');

    elements.erasRoot.innerHTML = '';
    state.eraMap.clear();
    state.segmentMap.clear();

    const prologue = buildPrologue(data.prologue);
    if (prologue) elements.erasRoot.appendChild(prologue);

    (data.eras || []).forEach((era) => {
      elements.erasRoot.appendChild(buildEra(era));
    });

    buildToc(data);
  };

  const renderError = (message) => {
    const problem = create('p', '', message);
    problem.style.padding = '14px 16px';
    problem.style.border = '1px solid rgba(141, 116, 72, 0.45)';
    problem.style.borderRadius = '10px';
    problem.style.background = 'rgba(255, 255, 255, 0.5)';
    elements.erasRoot.innerHTML = '';
    elements.erasRoot.appendChild(problem);
  };

  elements.expandAll?.addEventListener('click', () => setAllOpen(true));
  elements.collapseAll?.addEventListener('click', () => setAllOpen(false));

  fetch('./chronicle_data.json')
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Could not load chronicle_data.json (${response.status})`);
      }
      return response.json();
    })
    .then(render)
    .catch((error) => {
      console.error(error);
      renderError('Unable to load chronicle data. Confirm chronicle_data.json is available.');
    });
})

initSagaPage();