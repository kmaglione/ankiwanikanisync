import type { KeiseiJSON, WKSubject } from "./types.js";
export interface TemplateFields {
  Card: "Reading" | "Meaning";
  card_id: number;
  sort_id: string;
  components: string;
  Level: number;
  DocumentURL: string;
  Characters: string;
  Card_Type: "Radical" | "Kanji" | "Vocabulary" | "Kana Vocabulary";
  Word_Type: string;
  Meaning: string;
  Meaning_Mnemonic: string;
  Meaning_Hint: string;
  Meaning_Whitelist: string;
  Reading: string;
  Reading_Onyomi: string;
  Reading_Kunyomi: string;
  Reading_Nanori: string;
  Reading_Whitelist: string;
  Reading_Mnemonic: string;
  Reading_Hint: string;
  Components_Characters: string;
  Components_Meaning: string;
  Components_Reading: string;
  Similar_Characters: string;
  Similar_Meaning: string;
  Similar_Reading: string;
  Found_in_Characters: string;
  Found_in_Meaning: string;
  Found_in_Reading: string;
  Context_Patterns: string;
  Context_Sentences: string;
  Audio: string;
  Keisei: KeiseiJSON;
  last_upstream_sync_time: string;
  raw_data: WKSubject;
}

type DeepReadonly_<T>
    = T extends (infer V)[] ? readonly DeepReadonly<V>[]
    : T extends object ? Readonly<{ [K in keyof T]: DeepReadonly<T[K]> }>
    : T;

export type DeepReadonly<T>
    = T extends [...infer U extends unknown[]] ? readonly [...DeepReadonly_<U>]
    : DeepReadonly_<T>;

declare global {
  var _: DeepReadonly<TemplateFields>;
}
