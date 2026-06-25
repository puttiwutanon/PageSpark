/**
 * components/MathText.jsx
 *
 * Renders a string that may contain inline LaTeX ($...$) and block LaTeX ($$...$$)
 * WITHOUT any external dependencies (no WebView, no KaTeX).
 *
 * Supports:
 *  - Greek letters: \alpha, \beta, \gamma, \delta, \theta, \lambda, \mu, \pi,
 *                   \sigma, \omega, \phi, \psi, \Omega, \Delta, \Sigma, \Pi, etc.
 *  - Operators:     \times, \div, \cdot, \pm, \mp, \leq, \geq, \neq, \approx,
 *                   \equiv, \infty, \partial, \nabla, \sqrt{}, \frac{}{}, ^, _
 *  - Arrows:        \to, \leftarrow, \rightarrow, \Rightarrow, \Leftarrow, \leftrightarrow
 *  - Sets/logic:    \in, \notin, \subset, \cup, \cap, \forall, \exists, \neg
 *  - Misc:          \sum, \int, \prod, \lim, \log, \ln, \sin, \cos, \tan
 *
 * Usage:
 *   <MathText style={styles.someText}>
 *     งานที่แรงเสียดทาน $W_f = -fS$ กระทำต่อวัตถุ
 *   </MathText>
 *
 *   <MathText style={styles.someText}>
 *     The formula is $$E = mc^2$$ where c is light speed.
 *   </MathText>
 */

import React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import AppText from './appText';

// ─── Unicode symbol map ────────────────────────────────────────────────────────

const SYMBOLS = {
  // Greek lowercase
  alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε',
  zeta: 'ζ', eta: 'η', theta: 'θ', iota: 'ι', kappa: 'κ',
  lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', pi: 'π',
  rho: 'ρ', sigma: 'σ', tau: 'τ', upsilon: 'υ', phi: 'φ',
  chi: 'χ', psi: 'ψ', omega: 'ω',
  // Greek uppercase
  Alpha: 'Α', Beta: 'Β', Gamma: 'Γ', Delta: 'Δ', Epsilon: 'Ε',
  Theta: 'Θ', Lambda: 'Λ', Xi: 'Ξ', Pi: 'Π', Sigma: 'Σ',
  Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω',
  // Operators
  times: '×', div: '÷', cdot: '·', pm: '±', mp: '∓',
  leq: '≤', geq: '≥', neq: '≠', approx: '≈', equiv: '≡',
  sim: '∼', simeq: '≃', cong: '≅', propto: '∝',
  infty: '∞', partial: '∂', nabla: '∇', hbar: 'ℏ',
  // Set / logic
  in: '∈', notin: '∉', subset: '⊂', subseteq: '⊆',
  supset: '⊃', supseteq: '⊇', cup: '∪', cap: '∩',
  emptyset: '∅', forall: '∀', exists: '∃', nexists: '∄',
  neg: '¬', land: '∧', lor: '∨',
  // Arrows
  to: '→', leftarrow: '←', rightarrow: '→',
  Leftarrow: '⇐', Rightarrow: '⇒',
  leftrightarrow: '↔', Leftrightarrow: '⇔',
  uparrow: '↑', downarrow: '↓',
  // Misc math
  sum: '∑', int: '∫', prod: '∏', oint: '∮',
  lim: 'lim', log: 'log', ln: 'ln',
  sin: 'sin', cos: 'cos', tan: 'tan',
  arcsin: 'arcsin', arccos: 'arccos', arctan: 'arctan',
  sinh: 'sinh', cosh: 'cosh', tanh: 'tanh',
  max: 'max', min: 'min', sup: 'sup', inf: 'inf',
  det: 'det', dim: 'dim', ker: 'ker', deg: 'deg',
  gcd: 'gcd', mod: 'mod', exp: 'exp',
  // Dots
  cdots: '⋯', ldots: '…', vdots: '⋮', ddots: '⋱',
  // Brackets / delimiters (rendered as plain chars)
  langle: '⟨', rangle: '⟩', lfloor: '⌊', rfloor: '⌋',
  lceil: '⌈', rceil: '⌉',
  // Fractions shortcuts
  'frac{1}{2}': '½', 'frac{1}{3}': '⅓', 'frac{2}{3}': '⅔',
  'frac{1}{4}': '¼', 'frac{3}{4}': '¾',
  // Accents (drop the accent, keep letter — best effort without layout engine)
  // Geometry / physics common
  perp: '⊥', parallel: '∥', angle: '∠', measuredangle: '∡',
  triangle: '△', square: '□', circ: '∘',
  // Misc
  prime: '′', dprime: '″', degree: '°',
  copyright: '©', dagger: '†', ddagger: '‡',
  star: '★', bullet: '•',
};

// Superscript Unicode digits/letters
const SUPERSCRIPTS = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
  '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
  'n': 'ⁿ', 'i': 'ⁱ', 'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ',
  'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ',
  'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'o': 'ᵒ',
  'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
  'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
};

// Subscript Unicode digits
const SUBSCRIPTS = {
  '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
  '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
  '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
  'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'h': 'ₕ',
  'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'p': 'ₚ',
  'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ', 'v': 'ᵥ',
  'i': 'ᵢ', 'j': 'ⱼ',
};

// ─── LaTeX → Unicode string converter ─────────────────────────────────────────

/**
 * Convert a LaTeX string (without outer $ delimiters) to a Unicode string.
 * Handles: \command, ^{...} / ^x, _{...} / _x, \frac{}{}, \sqrt{}, \text{}
 */
function latexToUnicode(latex) {
  let s = latex.trim();

  // 1. \frac{num}{den}  →  (num)/(den)  or Unicode fraction if available
  s = s.replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, (_, num, den) => {
    // Check shortcut map first
    const key = `frac{${num}}{${den}}`;
    if (SYMBOLS[key]) return SYMBOLS[key];
    return `(${latexToUnicode(num)})/(${latexToUnicode(den)})`;
  });

  // 2. \sqrt{expr}  →  √(expr)
  s = s.replace(/\\sqrt\{([^}]*)\}/g, (_, expr) => `√(${latexToUnicode(expr)})`);

  // 3. \sqrt without braces (single char)  →  √x
  s = s.replace(/\\sqrt([^{])/g, (_, ch) => `√${ch}`);

  // 4. \text{...}  →  content as-is
  s = s.replace(/\\text\{([^}]*)\}/g, (_, t) => t);

  // 5. \overline{expr}  →  expr̄  (combining overline)
  s = s.replace(/\\overline\{([^}]*)\}/g, (_, expr) => `${latexToUnicode(expr)}\u0305`);

  // 6. \vec{expr}  →  expr⃗
  s = s.replace(/\\vec\{([^}]*)\}/g, (_, expr) => `${latexToUnicode(expr)}\u20D7`);

  // 7. \hat{expr}  →  expr̂
  s = s.replace(/\\hat\{([^}]*)\}/g, (_, expr) => `${latexToUnicode(expr)}\u0302`);

  // 8. Named symbols  e.g. \alpha  →  α
  s = s.replace(/\\([A-Za-z]+)/g, (match, name) => {
    return SYMBOLS[name] !== undefined ? SYMBOLS[name] : match;
  });

  // 9. Superscripts  ^{...} or ^x
  s = s.replace(/\^\{([^}]*)\}/g, (_, content) => {
    return [...content].map(c => SUPERSCRIPTS[c] || c).join('');
  });
  s = s.replace(/\^([^{])/g, (_, ch) => SUPERSCRIPTS[ch] || `^${ch}`);

  // 10. Subscripts  _{...} or _x
  s = s.replace(/_\{([^}]*)\}/g, (_, content) => {
    return [...content].map(c => SUBSCRIPTS[c] || c).join('');
  });
  s = s.replace(/_([^{])/g, (_, ch) => SUBSCRIPTS[ch] || `_${ch}`);

  // 11. Strip leftover curly braces used for grouping
  s = s.replace(/[{}]/g, '');

  return s;
}

// ─── Segment parser ────────────────────────────────────────────────────────────

function parseSegments(text) {
  const regex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }
    const raw = match[0];
    const isBlock = raw.startsWith('$$');
    const latex = isBlock ? raw.slice(2, -2).trim() : raw.slice(1, -1).trim();
    parts.push({ type: isBlock ? 'block' : 'inline', content: latex });
    lastIndex = match.index + raw.length;
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return parts;
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function MathText({ children, style, mathStyle }) {
  if (typeof children !== 'string') {
    return <AppText style={style}>{children}</AppText>;
  }

  const segments = parseSegments(children);

  // No math found — fast path
  if (segments.length === 1 && segments[0].type === 'text') {
    return <AppText style={style}>{children}</AppText>;
  }

  const flatStyle = StyleSheet.flatten(style) || {};
  const fontSize = flatStyle.fontSize || 16;
  const color = flatStyle.color || '#e2e8f0';

  const inlineMathStyle = [
    styles.inlineMath,
    { fontSize, color },
    mathStyle,
  ];

  const blockMathStyle = [
    styles.blockMath,
    { fontSize: fontSize + 1, color },
    mathStyle,
  ];

  return (
    <View style={styles.container}>
      {segments.map((seg, i) => {
        if (seg.type === 'text') {
          return (
            <AppText key={i} style={style}>
              {seg.content}
            </AppText>
          );
        }

        const unicode = latexToUnicode(seg.content);

        if (seg.type === 'block') {
          return (
            <View key={i} style={styles.blockWrapper}>
              <Text style={blockMathStyle}>{unicode}</Text>
            </View>
          );
        }

        // inline
        return (
          <Text key={i} style={inlineMathStyle}>
            {unicode}
          </Text>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'column',
  },
  inlineMath: {
    fontFamily: 'serif',          // serif renders math Unicode better on both platforms
  },
  blockMath: {
    fontFamily: 'serif',
    textAlign: 'center',
  },
  blockWrapper: {
    width: '100%',
    paddingVertical: 6,
    alignItems: 'center',
  },
});