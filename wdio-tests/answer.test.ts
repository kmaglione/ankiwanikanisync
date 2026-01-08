import { card } from "./card.ts";
import type { CardType } from "./card.ts";
import fixture from "../dist/fixtures/tests.test_importer.test_import_input_fixture.json" with { type: "json" };

async function checkTypos(cardType: CardType, input: string): Promise<string> {
    await card.showFront(cardType, fixture.kanji.病);
    await card.typeAnswer(input);
    await card.showBack();
    return $("#typos").getText();
}

describe("Answer input in Reading cards", () => {
    before(async () => {
        await card.showFront("Reading", fixture.kanji.病);
    });
    it("Should accept a correct reading", async () => {
        const result = await card.typeAnswer("byou");
        expect(result).toEqual({
            value: "びょう",
            submitted: "びょう",
            shook: false,
        });
    });
    it("Should accept an incorrect reading", async () => {
        const result = await card.typeAnswer("byoo");
        expect(result).toEqual({
            value: "びょお",
            submitted: "びょお",
            shook: false,
        });
    });
    it("Should convert a single trailing n to kana", async () => {
        const result = await card.typeAnswer("byon");
        expect(result).toEqual({
            value: "びょん",
            submitted: "びょん",
            shook: false,
        });
    });
    it("Should reject a correct but non-accepted reading", async () => {
        const result = await card.typeAnswer("yamai");
        expect(result).toEqual({
            value: "やまい",
            submitted: undefined,
            shook: true,
        });
    });
    it("Should reject mixed kana and kanji", async () => {
        const result = await card.typeAnswer("sickly");
        expect(result).toEqual({
            value: "しckly",
            submitted: undefined,
            shook: true,
        });
    });
    it("Should reject an accepted meaning", async () => {
        const result = await card.typeAnswer("coma");
        expect(result).toEqual({
            value: "こま",
            submitted: undefined,
            shook: true,
        });
    });
});

describe("Answer input in Meaning cards", () => {
    before(async () => {
        await card.showFront("Meaning", fixture.kanji.病);
    });
    it("Should accept a correct meaning", async () => {
        const result = await card.typeAnswer("sick");
        expect(result).toEqual({
            value: "sick",
            submitted: "sick",
            shook: false,
        });
    });
    it("Should accept an incorrect reading", async () => {
        const result = await card.typeAnswer("sickly");
        expect(result).toEqual({
            value: "sickly",
            submitted: "sickly",
            shook: false,
        });
    });
    it("Should reject a correct reading", async () => {
        const result = await card.typeAnswer("yamai");
        expect(result).toEqual({
            value: "yamai",
            submitted: undefined,
            shook: true,
        });
    });
});

describe("Typo detection for Meaning cards", () => {
    it("Should detect typos for accepted answers", async () => {
        const typos = await checkTypos("Meaning", "fli");
        expect(typos).toEqual("Did you mean flu instead of fli?");
        await expect($("#typeans")).toHaveElementClass("incorrect");
    });
    it("Should not typos for blacklisted answers", async () => {
        const typos = await checkTypos("Meaning", "fly");
        expect(typos).toEqual("");
        await expect($("#typeans")).toHaveElementClass("incorrect");
    });
    it("Should not report typos for correct answers", async () => {
        const typos = await checkTypos("Meaning", "sick");
        expect(typos).toEqual("");
        await expect($("#typeans")).toHaveElementClass("correct");
    });
});

describe("Typo detection for Reading cards", () => {
    it("Should detect typos for accepted answers", async () => {
        const typos = await checkTypos("Reading", "byuu");
        expect(typos).toEqual("Did you mean びょう instead of びゅう?");
        await expect($("#typeans")).toHaveElementClass("incorrect");
    });
    it("Should not report typos for correct answers", async () => {
        const typos = await checkTypos("Reading", "byou");
        expect(typos).toEqual("");
        await expect($("#typeans")).toHaveElementClass("correct");
    });
});
