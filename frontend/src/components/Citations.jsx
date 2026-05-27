/**
 * Renders a compact list of source citations for an assistant message.
 * Each citation shows its index number and the originating source/org.
 */
export default function Citations({ citations }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="citations" aria-label="Sources">
      <span className="citations-label">Sources:</span>
      {citations.map((c) => (
        <span key={c.index} className="citation-chip" title={c.filename}>
          [{c.index}] {c.source.toUpperCase()}
        </span>
      ))}
    </div>
  );
}
