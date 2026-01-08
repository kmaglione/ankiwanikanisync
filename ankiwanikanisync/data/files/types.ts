type int = number;
export type AssignmentID = int;
export type DateString = string;
export type SRSID = int;
export type SubjectId = int;
export type SubjectType = "kana_vocabulary" | "kanji" | "radical" | "vocabulary";
export type WKLevel = int;

export interface WKResponsePages {
    per_page: int;
    next_url: string | null;
    previous_url: string | null;
}

export interface WKResponse {
    object: string;
    url: string;
    data_updated_at: DateString | null;
}

export interface WKCollectionResponse extends WKResponse {
    pages: WKResponsePages;
    total_count: int;
}

export interface WKMeaning {
    meaning: string;
    primary: boolean;
    accepted_answer: boolean;
}

export interface WKAuxMeaning {
    meaning: string;
    type: "whitelist" | "blacklist";
}

type WKReadingType = "kunyomi" | "nanori" | "onyomi";

export interface WKReading {
    reading: string;
    primary: boolean;
    accepted_answer: boolean;
    type?: WKReadingType;
}

export interface WKContextSentence {
    en: string;
    ja: string;
}

export interface WKAudioMetadata {
    gender: "male" | "female";
    source_id: int;
    pronunciation: string;
    voice_actor_id: int;
    voice_actor_name: string;
    voice_description: string;
}

export interface WKAudio {
    url: string;
    content_type: string;
    metadata: WKAudioMetadata;
}

export interface WKSubjectDataBase {
    auxiliary_meanings: WKAuxMeaning[];
    characters: string;
    created_at: DateString;
    document_url: string;
    hidden_at: DateString | null;
    lesson_position: int;
    level: WKLevel;
    meaning_mnemonic: string;
    meanings: WKMeaning[];
    slug: string;
    spaced_repetition_system_id: SRSID;
}

export interface WKReadable {
    readings: WKReading[];
}

export interface WKComponentData extends WKSubjectDataBase {
    amalgamation_subject_ids: SubjectId[];
}

export interface WKAssignmentData {
    available_at: null | DateString;
    burned_at: null | DateString;
    created_at: DateString;
    hidden: boolean;
    passed_at: null | DateString;
    resurrected_at: null | DateString;
    srs_stage: int;
    started_at: null | DateString;
    subject_id: int;
    subject_type: SubjectType;
    unlocked_at: null | DateString;
}

export interface WKAssignment extends WKResponse {
    id: AssignmentID;
    data: WKAssignmentData;
}

export interface WKAssignmentsResponse extends WKCollectionResponse {
    data: WKAssignment[];
}

export interface WKStudyMaterialData {
    created_at: DateString;
    hidden: boolean;
    meaning_note: string;
    meaning_synonyms: string[];
    reading_note: string;
    subject_id: int;
    subject_type: SubjectType;
}

export interface WKStudyMaterial extends WKResponse {
    id: int;
    data: WKStudyMaterialData;
}

export interface WKStudyMaterialsResponse extends WKCollectionResponse {
    data: WKStudyMaterial[];
}

export type WKSubscriptionType = "free" | "recurring" | "lifetime";

export interface WKSubscription {
    active: boolean;
    max_level_granted: WKLevel;
    period_ends_at: null | DateString;
    type: WKSubscriptionType;
}

export interface WKPreferences {
    default_voice_actor_id: int;
    extra_study_autoplay_audio: boolean;
    lessons_autoplay_audio: boolean;
    lessons_batch_size: int;
    lessons_presentation_order: "ascending_level_then_subject";
    reviews_autoplay_audio: boolean;
    reviews_display_srs_indicator: boolean;
    reviews_presentation_order: "shuffled" | "lower_levels_first";
}

export interface WKUserData {
    current_vacation_started_at: DateString | null;
    level: WKLevel;
    preferences: WKPreferences;
    profile_url: string;
    started_at: DateString;
    subscription: WKSubscription;
    username: string;
}

export interface WKUser extends WKResponse {
    data: WKUserData;
}

export interface WKSRSStageBase {
    position: int;
}

export interface WKSRSStageEmpty extends WKSRSStageBase {
    interval: null;
    interval_unit: null;
}

export type IntervalUnit = "milliseconds" | "seconds" | "minutes" | "hours" | "days" | "weeks";

export interface WKSRSStageNonEmpty extends WKSRSStageBase {
    interval: int;
    interval_unit: IntervalUnit;
}

export type WKSpacedRepetitionSystemStage = WKSRSStageNonEmpty | WKSRSStageEmpty;

export interface WKSpacedRepetitionSystemData {
    burning_stage_position: int;
    created_at: DateString;
    description: string;
    name: string;
    passing_stage_position: int;
    stages: WKSpacedRepetitionSystemStage[];
    starting_stage_position: int;
    unlocking_stage_position: int;
}

export interface WKSpacedRepetitionSystem extends WKResponse {
    data: WKSpacedRepetitionSystemData;
}

export interface WKCharacterImageMetadata {
    inline_styles?: boolean;
}

export interface WKCharacterImage {
    url: string;
    content_type: string;
    metadata: WKCharacterImageMetadata;
}

export interface WKRadicalData extends WKComponentData {
    character_images: WKCharacterImage[];
}

export interface WKAmalgumData {
    component_subject_ids: SubjectId[];
}

export interface WKKanjiData extends WKAmalgumData, WKComponentData, WKReadable {
    meaning_hint: string | null;
    reading_hint: string | null;
    reading_mnemonic: string;
    visually_similar_subject_ids: SubjectId[];
}

export interface WKVocabBase extends WKSubjectDataBase {
    context_sentences: WKContextSentence[];
    parts_of_speech: string[];
    pronunciation_audios: WKAudio[];
}

export interface WKVocabData extends WKAmalgumData, WKVocabBase, WKReadable {
    reading_mnemonic: string;
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export interface WKKanaVocabData extends WKVocabBase {}

export type WKSubjectData
    = WKKanaVocabData
        | WKKanjiData
        | WKRadicalData
        | WKVocabData;

export interface WKSubject<T = WKSubjectData> extends WKResponse {
    id: int;
    data: T;
}

export interface WKSubjectsResponse extends WKCollectionResponse {
    data: WKSubject[];
}

export interface RelatedSubject {
    characters: string;
    reading: string;
    meaning: string;
}

export interface KeiseiCompound {
    character: string;
    reading: string;
    meaning: string;
}

export interface KeiseiJSON {
    compounds?: KeiseiCompound[];
    component?: string;
    kanji?: [string, string];
    radical?: string;
    readings?: string[];
    semantic?: string;
    type: string;
}
