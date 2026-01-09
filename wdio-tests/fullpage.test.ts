import { browser } from "@wdio/globals";

import { card } from "./card.ts";
import type { CardType } from "./card.ts";
import ctxt from "../dist/fixtures/tests.test_importer.test_import_context_patterns.json" with { type: "json" };
import imp from "../dist/fixtures/tests.test_importer.test_import_fields.json" with { type: "json" };

const notes = [
    imp.radical.口,
    imp.kanji.右,
    imp.vocabulary.左右,
    ctxt.vocabulary.右,
];

async function saveScreenshot(name: string) {
    // await argosScreenshot(browser, name);
    await browser.saveScreenshot(`./screenshots/argos/${name}.png`, { fullPage: true });
}

describe("Full page screenshots", () => {
    before(async () => {
        await browser.setViewport({ width: 800, height: 600 });
    });
    after(async () => {
        await browser.setWindowSize(800, 800);
    });
    for (const cardType of ["Meaning", "Reading"] satisfies CardType[]) {
        describe(`${cardType} cards`, () => {
            for (const note of notes) {
                const char = note["Characters"];
                if (cardType === "Meaning" || note["Card_Type"] !== "Radical") {
                    describe(`${note["Card_Type"]} ${char}`, function () {
                        it("Should have the correct front", async () => {
                            await card.showFront(cardType, note);
                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-front`);
                        });
                        it("Should have the correct initial back", async () => {
                            await card.showBack();
                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-back-initial`);
                        });
                        it("Should have the correct expanded back", async () => {
                            await card.openSections("details");
                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-back-expanded`);
                        });
                    });
                }
            }
        });
    }
});
