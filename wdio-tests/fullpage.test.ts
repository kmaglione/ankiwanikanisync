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
        await card.setNightMode(false);
        await card.setMobile(false);
    });
    for (const mobile of [false, true]) {
        describe(`mobile=${mobile}`, () => {
            before(async () => {
                await card.setMobile(mobile);
                if (mobile) {
                    await browser.setViewport({ width: 550, height: 800 });
                } else {
                    await browser.setViewport({ width: 800, height: 600 });
                }
            });

            const mobileSuffix = mobile ? "-mobile" : "";
            for (const nightMode of [false, true]) {
                const suffix = (nightMode ? "-night-mode" : "") + mobileSuffix;
                describe(`nightMode=${nightMode}`, () => {
                    before(async () => {
                        await card.setNightMode(nightMode);
                    });
                    for (const cardType of ["Meaning", "Reading"] satisfies CardType[]) {
                        describe(`${cardType} cards`, () => {
                            for (const note of notes) {
                                const char = note["Characters"];
                                if (cardType === "Meaning" || note["Card_Type"] !== "Radical") {
                                    describe(`${note["Card_Type"]} ${char}`, function () {
                                        it("Should have the correct front", async () => {
                                            await card.showFront(cardType, note);
                                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-front${suffix}`);
                                        });
                                        it("Should have the correct initial back", async () => {
                                            await card.showBack();
                                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-back-initial${suffix}`);
                                        });
                                        it("Should have the correct expanded back", async () => {
                                            await card.openSections("details");
                                            await saveScreenshot(`full-page-${note["Card_Type"]}-${char}-${cardType}-back-expanded${suffix}`);
                                        });
                                    });
                                }
                            }
                        });
                    }
                    describe("Answer styling", () => {
                        it("Should have the correct front styling", async () => {
                            await card.showFront("Reading", imp.vocabulary.左右);
                            await card.typeAnswer("さゆう");
                            await saveScreenshot(`full-page-answer-front${suffix}`);
                        });
                        it("Should have the correct back styling for correct answers", async () => {
                            await card.showBack();
                            await saveScreenshot(`full-page-answer-back-correct${suffix}`);
                        });
                        it("Should have the correct back styling for typos", async () => {
                            await card.showFront("Reading", imp.vocabulary.左右);
                            await card.typeAnswer("さゆー");
                            await card.showBack();
                            await saveScreenshot(`full-page-answer-back-typo${suffix}`);
                        });
                    });
                });
            }
        });
    }
});
