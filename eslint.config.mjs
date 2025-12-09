import html from "eslint-plugin-html"
import typescriptParser from "@typescript-eslint/parser";
import ts from 'typescript-eslint';
import js from "@eslint/js";
import globals from "globals";
import { defineConfig } from "eslint/config";

const noUnusedVars = ["error", {
    "argsIgnorePattern": "^_",
    "caughtErrorsIgnorePattern": "^_",
    "varsIgnorePattern": "^_",
}];

export default defineConfig([
    {
        files: ["**/*.{js,mjs,cjs}"],
        plugins: { js },
        extends: ["js/recommended"],
        languageOptions: { globals: globals.browser },
        rules: {
            "no-unused-vars": noUnusedVars,
        },
    },
    {
        files: ["**/*.{ts,mts}"],
        plugins: { js, ts },
        extends: ["js/recommended", "ts/recommendedTypeChecked"],
        languageOptions: {
            globals: globals.browser,
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
        languageOptions: { globals: globals.browser },
        rules: {
            "no-constant-binary-expression": "off",
            "no-constant-condition": "off",
        }
    },
]);
