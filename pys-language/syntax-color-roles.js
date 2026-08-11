/**
 * Shared TextMate role → scope map (packaged with the VSIX).
 * Build script `scripts/apply-syntax-colors.js` and runtime UI both use this.
 */
/** @type {Record<string, { scope: string[] }>} */
const ROLE_SCOPES = {
  comments: {
    scope: ['comment.line.number-sign.pys', 'comment.block.pys'],
  },
  strings: {
    scope: ['string.quoted.double.pys', 'string.quoted.single.pys'],
  },
  numbers: {
    scope: [
      'constant.numeric.integer.pys',
      'constant.numeric.float.pys',
      'constant.numeric.hex.pys',
      'constant.numeric.binary.pys',
      'constant.language.pys',
      'constant.character.escape.pys',
    ],
  },
  functions: {
    scope: ['entity.name.function.pys', 'support.function.pys'],
  },
  types: {
    scope: [
      'storage.type.primitive.pys',
      'entity.name.type.pys',
      'entity.name.type.class.pys',
      'entity.name.type.interface.pys',
      'entity.name.type.struct.pys',
      'entity.name.type.data.pys',
      'entity.name.type.entity.pys',
      'entity.name.type.enum.pys',
    ],
  },
  'language-constants': {
    scope: ['variable.language.pys', 'variable.other.constant.pys'],
  },
  keywords: {
    scope: [
      'keyword.control.pys',
      'keyword.operator.pys',
      'storage.modifier.pys',
      'punctuation.definition.decorator.pys',
      'entity.name.function.decorator.pys',
      'meta.function.decorator.pys',
    ],
  },
};

const THEME_KEYS = {
  dark: '[*Dark*]',
  light: '[*Light*]',
  'high-contrast': '[*HighContrast*]',
};

module.exports = {
  ROLE_SCOPES,
  THEME_KEYS,
};
