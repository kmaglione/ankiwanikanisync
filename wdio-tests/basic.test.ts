import { expect } from "@wdio/globals";

import { card } from "./card.ts";
import fixture from "../dist/fixtures/tests.test_importer.test_import_fields.json" with { type: "json" };

describe("Basic Reading functionality", () => {
    it("should have appropriate headings", async () => {
        await card.showFront("Reading", fixture.vocabulary.七);
        await card.showBack();

        const headings = await card.getHeadings();
        expect(headings).toEqual(["Reading", "Meaning", "Context"]);
    });
});

describe("Basic Meaning functionality", () => {
    it("should have appropriate headings", async () => {
        await card.showFront("Meaning", fixture.vocabulary.七);
        await card.showBack();

        const headings = await card.getHeadings();
        expect(headings).toEqual(["Meaning", "Reading", "Context"]);
    });
});
