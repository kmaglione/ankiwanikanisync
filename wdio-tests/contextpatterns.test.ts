import { card } from "./card.ts";
import type { CardType } from "./card.ts";
import { matchElementSnapshot } from "./util.ts";
import imp from "../dist/fixtures/tests.test_importer.test_import_context_patterns.json" with { type: "json" };

for (const cardType of ["Meaning", "Reading"] satisfies CardType[]) {
    describe(`Context pattern elements in ${cardType} cards`, () => {
        before(async () => {
            await card.showFront(cardType, imp.vocabulary.右);
            await card.showBack();

            await card.openSection("#section-context > details");
        });
        it("Should have the correct buttons", async () => {
            const buttons = await $$("#patterns-of-use button").map(b => b.getText());
            expect(buttons).toEqual(["右の〜", "右〜"]);
        });
        it("Should have the initial text", async () => {
            const text = await $("#common-word-combinations").getText();
            expect(text).toEqual(
                "Common Word Combinations\n"
                + "右のボタン\nright button\n"
                + "右のグラフ\ngraph on the right\n"
                + "右のアイコン\nright icon");
        });
        it("Should have the correct initial visual", async function () {
            this.retries(4);
            await matchElementSnapshot($("#context-patterns"), `context-patterns-${cardType}`);
        });
        it("Should have the text after selection", async () => {
            await $("button=右〜").click();
            await $("body").click();
            await browser.pause(500);

            const text = await $("#common-word-combinations").getText();
            expect(text).toEqual(
                "Common Word Combinations\n"
                + "右上\nupper right\n"
                + "右ひざ\nright knee\n"
                + "右下\nlower right");
        });
        it("Should have the correct visual after selection", async function () {
            this.retries(4);
            await matchElementSnapshot($("#context-patterns"), `context-patterns-2-${cardType}`);
        });
    });
}
