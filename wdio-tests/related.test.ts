import { expect } from "@wdio/globals";

import { card } from "./card.ts";
import type { CardType } from "./card.ts";
import { matchElementSnapshot } from "./util.ts";
import fixture from "../dist/fixtures/tests.test_importer.test_import_fields.json" with { type: "json" };

for (const cardType of ["Meaning", "Reading"] satisfies CardType[]) {
    describe(`Related elements in ${cardType} cards`, () => {
        describe("Visually Similar Kanji", function () {
            before(async () => {
                await card.showFront(cardType, fixture.kanji.人);
                await card.showBack();

                await $("#box-title").click();
            });

            it("Should have the correct section heading", async () => {
                expect(await $("#box-title").getText()).toEqual("Visually Similar Kanji");
            });

            it("Should have the correct text", async () => {
                expect(await $("#box-container").getText()).toEqual("入\nにゅう\nEnter");
            });

            it("Should have the correct visual", async function () {
                this.retries(4);
                await matchElementSnapshot($("#box-container"), `visually-similar-kanji-${cardType}`);
            });
        });

        describe("Kanji Composition", function () {
            before(async () => {
                await card.showFront(cardType, fixture.vocabulary.左右);
                await card.showBack();

                await $("#box-title").click();
            });

            it("Should have the correct section heading", async () => {
                expect(await $("#box-title").getText()).toEqual("Kanji Composition");
            });

            it("Should have the correct text", async () => {
                expect(await $("#box-container").getText()).toEqual("右\nゆう\nRight\n左\nさ\nLeft");
            });

            it("Should have the correct visual", async function () {
                this.retries(4);
                await matchElementSnapshot($("#box-container"), `kanji-composition-${cardType}`);
            });
        });

        describe("Found in Vocabulary", function () {
            before(async () => {
                await card.showFront(cardType, fixture.kanji.左);
                await card.showBack();

                await $("#section-found-in-vocabulary .heading").click();
            });

            it("Should have the correct section headings", async () => {
                expect(await card.getHeadings()).toContain("Found in Vocabulary");
            });

            it("Should have the correct text", async () => {
                expect(await $("#found-in-vocabulary-container").getText()).toEqual("左右\nさゆう\nLeft And Right");
            });

            it("Should have the correct visual", async function () {
                this.retries(4);
                await matchElementSnapshot($("#found-in-vocabulary-container"), `found-in-vocabulary-${cardType}`);
            });
        });

        if (cardType === "Meaning") {
            describe("Found In Kanji", function () {
                before(async () => {
                    await card.showFront(cardType, fixture.radical.口);
                    await card.showBack();

                    await $("#box-title").click();
                });

                it("Should have the correct section heading", async () => {
                    expect(await $("#box-title").getText()).toEqual("Found In Kanji");
                });

                it("Should have the correct text", async () => {
                    expect(await $("#box-container").getText()).toEqual("右\nゆう\nRight");
                });

                it("Should have the correct visual", async function () {
                    this.retries(4);
                    await matchElementSnapshot($("#box-container"), "found-in-kanji");
                });
            });
        }
    });
}
