import path from "node:path";

import { includeIgnoreFile } from "@eslint/compat";
import type { RuleConfig } from "@eslint/core";
import js from "@eslint/js";
import stylistic from "@stylistic/eslint-plugin";
import typescriptParser from "@typescript-eslint/parser";
import { defineConfig, globalIgnores } from "eslint/config";
import type { Config } from "eslint/config";
import html from "eslint-plugin-html";
import importPlugin from "eslint-plugin-import";
import globals from "globals";
import ts from "typescript-eslint";

const noUnusedVars: RuleConfig = ["error", {
    argsIgnorePattern: "^_",
    caughtErrorsIgnorePattern: "^_",
    varsIgnorePattern: "^_",
}];

const allGlobals = {
    ...globals.browser,
    pycmd: "readonly",
};

const jsBase: Config = {
    rules: {
        "eqeqeq": ["error", "always", { null: "ignore" }],
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
    includeIgnoreFile(path.join(import.meta.dirname, ".gitignore")),
    globalIgnores([
        "**/*.min.js",
    ]),
    stylistic.configs.customize({
        braceStyle: "1tbs",
        commaDangle: "always-multiline",
        indent: 4,
        jsx: false,
        quotes: "double",
        semi: true,
    }),
    {
        rules: {
            "@stylistic/arrow-parens": ["error", "as-needed"],
            "@stylistic/indent": ["error", 4, {
                ArrayExpression: 1,
                CallExpression: { arguments: "first" },
                flatTernaryExpressions: true,
                FunctionDeclaration: { body: 1, parameters: "first", returnType: 1 },
                FunctionExpression: { body: 1, parameters: "first", returnType: 1 },
                ignoreComments: false,
                ignoredNodes: ["TSUnionType", "TSIntersectionType"],
                ImportDeclaration: 1,
                MemberExpression: 1,
                ObjectExpression: 1,
                offsetTernaryExpressions: false,
                outerIIFEBody: 1,
                SwitchCase: 0,
                VariableDeclarator: 1,
            }],
            "@stylistic/indent-binary-ops": ["error", 4],
            "@stylistic/quotes": ["error", "double", { avoidEscape: true, allowTemplateLiterals: "avoidEscape" }],
        },
    },
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
            "@typescript-eslint/no-explicit-any": "off",
            "@typescript-eslint/prefer-readonly": "error",
        },
    },
    {
        files: ["**/*.html"],
        plugins: { js, html },
        extends: ["js/recommended"],
        languageOptions: { globals: allGlobals },
        rules: {
            "no-constant-binary-expression": "off",
            "no-constant-condition": "off",
        },
    },
]);
