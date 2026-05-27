import Citations from './Citations';

// -------------------------------------------------------
// Inline renderer: **bold**, *italic*, [n] citation markers
// -------------------------------------------------------
function renderInline(text, keyPrefix = '') {
  if (!text) return null;
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*|\[\d+\])/g);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (/^\*\*[^*]+\*\*$/.test(part)) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (/^\*[^*\n]+\*$/.test(part)) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    if (/^\[\d+\]$/.test(part)) {
      return <sup key={key} className="citation-marker">{part}</sup>;
    }
    return part;
  });
}

// -------------------------------------------------------
// Block parser: turns raw LLM text into structured blocks
// Handles: paragraphs, bullet lists (* / -), numbered lists,
//          headings (#), horizontal rules (---), blank lines
// -------------------------------------------------------
function parseBlocks(rawText) {
  const lines = rawText.split('\n');
  const blocks = [];
  let listType = null;
  let listItems = [];
  let paraLines = [];

  function flushPara() {
    const joined = paraLines.join(' ').trim();
    if (joined) blocks.push({ type: 'p', text: joined });
    paraLines = [];
  }

  function flushList() {
    if (listItems.length > 0) {
      blocks.push({ type: listType, items: [...listItems] });
    }
    listItems = [];
    listType = null;
  }

  for (const line of lines) {
    const trimmed = line.trim();

    // Blank line → flush current accumulator
    if (!trimmed) {
      flushPara();
      flushList();
      continue;
    }

    // Horizontal rule
    if (/^---+$/.test(trimmed)) {
      flushPara();
      flushList();
      blocks.push({ type: 'hr' });
      continue;
    }

    // Heading: # / ## / ###
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)/);
    if (headingMatch) {
      flushPara();
      flushList();
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      continue;
    }

    // Bullet list item: * text  or  - text  (handles *   **Bold** text)
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (bulletMatch) {
      flushPara();
      if (listType !== 'ul') { flushList(); listType = 'ul'; }
      listItems.push(bulletMatch[1].trim());
      continue;
    }

    // Nested bullet (indented): "    * text" or "    - text"
    const nestedBulletMatch = line.match(/^\s{2,}[-*•]\s+(.+)/);
    if (nestedBulletMatch && listType === 'ul') {
      // Append as a sub-item to the last item, using a dash separator
      if (listItems.length > 0) {
        listItems[listItems.length - 1] += '; ' + nestedBulletMatch[1].trim();
      } else {
        listItems.push(nestedBulletMatch[1].trim());
      }
      continue;
    }

    // Numbered list: 1. / 1) text
    const numberedMatch = trimmed.match(/^\d+[.)]\s+(.+)/);
    if (numberedMatch) {
      flushPara();
      if (listType !== 'ol') { flushList(); listType = 'ol'; }
      listItems.push(numberedMatch[1].trim());
      continue;
    }

    // Regular text — accumulate as paragraph
    // But if we were mid-list, this is a new paragraph
    if (listType) {
      flushList();
    }
    paraLines.push(trimmed);
  }

  flushPara();
  flushList();

  return blocks;
}

// -------------------------------------------------------
// Block renderer
// -------------------------------------------------------
function renderBlocks(blocks) {
  return blocks.map((block, i) => {
    switch (block.type) {
      case 'hr':
        return <hr key={i} className="msg-divider" />;

      case 'heading': {
        // Map LLM heading levels to sensible HTML levels (don't use h1/h2)
        const Tag = block.level <= 2 ? 'h3' : 'h4';
        return (
          <Tag key={i} className="msg-heading">
            {renderInline(block.text, `h${i}`)}
          </Tag>
        );
      }

      case 'p':
        return <p key={i}>{renderInline(block.text, `p${i}`)}</p>;

      case 'ul':
        return (
          <ul key={i} className="msg-list">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item, `ul${i}-${j}`)}</li>
            ))}
          </ul>
        );

      case 'ol':
        return (
          <ol key={i} className="msg-list msg-list--ol">
            {block.items.map((item, j) => (
              <li key={j}>{renderInline(item, `ol${i}-${j}`)}</li>
            ))}
          </ol>
        );

      default:
        return null;
    }
  });
}

// -------------------------------------------------------
// Message component
// -------------------------------------------------------
export default function Message({ message }) {
  const { role, content, citations, isEmergency } = message;
  const blocks = role === 'assistant' ? parseBlocks(content) : null;

  return (
    <div
      className={[
        'msg',
        `msg--${role}`,
        isEmergency ? 'msg--emergency' : '',
      ]
        .filter(Boolean)
        .join(' ')}
      role={role === 'assistant' ? 'log' : undefined}
      aria-live={role === 'assistant' ? 'polite' : undefined}
    >
      {role === 'assistant' && (
        <span className="msg-avatar" aria-hidden="true">
          {isEmergency ? '🚨' : '🩺'}
        </span>
      )}

      <div className="msg-body">
        <div className="msg-content">
          {role === 'assistant'
            ? renderBlocks(blocks)
            : <p>{content}</p>}
        </div>
        {citations && citations.length > 0 && (
          <Citations citations={citations} />
        )}
      </div>
    </div>
  );
}
