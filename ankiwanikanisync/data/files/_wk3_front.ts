/* globals _ */
import wanakana from "./_wanakana.min.js";
import { assert, assertNever, stripHTML, $ } from "./_wk3_util.js";

function map<T, U>(iter: Iterable<T>, fn: (arg: T) => U) {
    return Iterator.from(iter).map(fn);
}

export function setupFront() {
    const typeans = $("#typeans");

    const questionName = _.Card_Type === "Radical" ? "Name" : _.Card;

    const questionNameDiv = $("#question-name");
    questionNameDiv.innerHTML = `${_.Card_Type} <b>${questionName}</b>`;

    switch (_.Card) {
      case "Meaning":
        questionNameDiv.classList.add("meaning");
        break;
      case "Reading":
        questionNameDiv.classList.add("reading");
        typeans.setAttribute("lang", "ja");
    }

    const questionDisplayDiv = $("#question-display");
    switch (_.Card_Type) {
      case "Radical":
        questionDisplayDiv.classList.add("radical");
        break;
      case "Kanji":
        questionDisplayDiv.classList.add("kanji");
        break;
      case "Vocabulary":
      case "Kana Vocabulary":
        questionDisplayDiv.classList.add("vocabulary");
        break;
      default:
        assertNever();
    }

    if (typeans && (typeans instanceof HTMLInputElement ||
                    typeans instanceof HTMLTextAreaElement)) {
        if (_.Card === "Reading") {
            wanakana.bind(typeans);
        }

        typeans.setAttribute("placeholder", "Your Response");
        typeans.addEventListener("animationend", event => {
            assert(event.target instanceof Element);
            event.target.classList.remove("shake");
        });

        const meaningWhitelist = new Set(_.Meaning_Whitelist.split(", ")
                                          .map(s => s.toLowerCase()));

        const readingWhitelist = new Set(_.Reading_Whitelist.split(", ")
                                          .map(stripHTML));

        const readingAll = new Set(_.Reading_Onyomi.split(", ")
                                    .concat(_.Reading_Kunyomi.split(", "))
                                    .map(stripHTML));

        const readingWarning = readingAll.difference(readingWhitelist);

        let checkWarning = (_answers: Set<string>) => false;
        switch (_.Card) {
          case "Reading": {
            checkWarning = answers => {
                if (Iterator.from(answers).some(wanakana.isMixed)) {
                    return true;
                }

                if (answers.isSubsetOf(readingWhitelist)) {
                    return false;
                }

                const romaji = new Set(map(answers, s => wanakana.toRomaji(s).toLowerCase()));
                if (romaji.isSubsetOf(meaningWhitelist)) {
                    return true;
                }

                switch (_.Card_Type) {
                  case "Kanji":
                  case "Vocabulary":
                    return answers.isSubsetOf(readingAll)
                        && !answers.isDisjointFrom(readingWarning);
                }
                return false;
            };
            break;
          }
          case "Meaning": {
            checkWarning = answers => {
                if (answers.isSubsetOf(meaningWhitelist)) {
                    return false;
                }

                const kana = new Set(map(answers, wanakana.toKana));
                return kana.isSubsetOf(readingAll);
            };
          }
        }

        typeans.addEventListener("keypress", (event: KeyboardEvent) => {
            if (event.key === "Enter") {
                if (_.Card === "Reading" && typeans.value.endsWith("n")) {
                    typeans.value = typeans.value.slice(0, -1) + "ん";
                }

                const answers = new Set(typeans.value.split(/[、,]\s*/));
                if (answers.size
                        && checkWarning(answers)
                        && !typeans.classList.contains("shake")) {
                    typeans.classList.add("shake");
                    event.preventDefault();
                    event.stopPropagation();
                }
            }
        }, true);
    }
}
