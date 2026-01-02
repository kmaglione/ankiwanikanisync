import js from "@eslint/js";
import typescriptParser from "@typescript-eslint/parser";
import { defineConfig } from "eslint/config";
import html from "eslint-plugin-html";
import importPlugin from "eslint-plugin-import";
import globals from "globals";
import ts from 'typescript-eslint';

const noUnusedVars = ["error", {
    "argsIgnorePattern": "^_",
    "caughtErrorsIgnorePattern": "^_",
    "varsIgnorePattern": "^_",
}];

const allGlobals = {
    ...globals.browser,
    pycmd: "readonly",
};

const jsBase = {
    rules: {
        "import/no-unresolved": "off",
        "import/order": [
            "error",
            {
                "groups": ["builtin", "external", "internal", ["parent", "sibling", "index"]],
                "alphabetize": { order: "asc" },
                "named": true,
                "newlines-between": "always",
            },
        ],
    },
};

export default defineConfig([
    {
        files: ["**/*.{js,mjs,cjs}"],
        plugins: { js, import: importPlugin },
        extends: ["js/recommended", jsBase],
        languageOptions: { globals: allGlobals },
        rules: {
            "no-unused-vars": noUnusedVars,
        },
    },
    {
        files: ["**/*.{ts,mts}"],
        plugins: { js, ts },
        extends: [
            "js/recommended",
            "ts/recommendedTypeChecked",
            importPlugin.flatConfigs.recommended,
            importPlugin.flatConfigs.typescript,
            jsBase,
        ],
        languageOptions: {
            globals: allGlobals,
            parser: typescriptParser,
            parserOptions: {
                projectService: true,
            },
        },
        rules: {
            "no-unused-vars": "off",
            "@typescript-eslint/no-unused-vars": noUnusedVars,
            "@typescript-eslint/prefer-readonly": "error",
        }
    },
    {
        files: ["**/*.html"],
        plugins: { js, html },
        extends: ["js/recommended"],
        languageOptions: { globals: allGlobals },
        rules: {
            "no-constant-binary-expression": "off",
            "no-constant-condition": "off",
        }
    },
]);
