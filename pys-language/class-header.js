/**
 * Scan upward from fromLine for a class header (optional exact className).
 * @param {{ lineAt: (i: number) => { text: string } }} document
 * @param {number} fromLine
 * @param {string} [className]
 * @returns {{ line: number, classIndex: number, closed: boolean, closedIndex: number, alreadyAbstract: boolean } | null}
 */
function findEnclosingClassHeader(document, fromLine, className) {
  const namePat = className
    ? String(className).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    : '[A-Za-z_]\\w*';
  const re = new RegExp(
    `^(\\s*)((?:(?:global|package)\\s+)?)((?:abstract\\s+)?)((?:closed\\s+)?)(class\\s+)(${namePat})\\b`,
  );
  for (let i = fromLine; i >= 0; i -= 1) {
    const text = document.lineAt(i).text;
    const m = re.exec(text);
    if (!m) continue;
    const indent = m[1].length;
    const visLen = m[2].length;
    const abstractLen = m[3].length;
    const closedLen = m[4].length;
    return {
      line: i,
      classIndex: indent + visLen + abstractLen + closedLen,
      closed: closedLen > 0,
      closedIndex: indent + visLen + abstractLen,
      alreadyAbstract: abstractLen > 0,
    };
  }
  return null;
}

module.exports = { findEnclosingClassHeader };
