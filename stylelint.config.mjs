/** @type {import("stylelint").Config} */
export default {
  "extends": ["stylelint-config-standard"],
  "rules": {
      "keyframe-selector-notation": "keyword",
      "no-descending-specificity": null,
      "no-duplicate-selectors": null,
      "selector-class-pattern": null,
      "selector-type-no-unknown": [true, {
          "ignoreTypes": [
              "kanji",
              "ja",
              "radical",
              "radical-combination",
              "reading",
              "vocabulary",
              "wk-radical-svg",
          ],
      }],
  }
};
