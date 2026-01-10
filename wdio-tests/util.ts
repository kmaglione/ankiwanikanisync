import type { CheckElementMethodOptions, CheckFullPageMethodOptions, CheckScreenMethodOptions, SaveElementMethodOptions, SaveFullPageMethodOptions, SaveScreenMethodOptions } from "@wdio/image-comparison-core";

declare module "webdriverio" {
    interface ChainablePromiseArray {
        then<U>(
            res?: ((elem: WebdriverIO.ElementArray) => Promise<U> | U) | null,
            rej?: ((val: any) => Promise<U> | U) | null
        ): Promise<U>;
    }
}

export interface WdioIcsOptions {
    logName?: string;
    name?: string;
}
export interface WdioIcsCommonOptions {
    hideElements?: (WebdriverIO.Element | ChainablePromiseElement)[];
    removeElements?: (WebdriverIO.Element | ChainablePromiseElement)[];
}
export interface WdioIcsScrollOptions extends WdioIcsCommonOptions {
    hideAfterFirstScroll?: (WebdriverIO.Element | ChainablePromiseElement)[];
}
export interface WdioSaveScreenMethodOptions extends Omit<SaveScreenMethodOptions, keyof WdioIcsCommonOptions>, WdioIcsCommonOptions {
}
export interface WdioSaveElementMethodOptions extends Omit<SaveElementMethodOptions, keyof WdioIcsCommonOptions>, WdioIcsCommonOptions {
}
export interface WdioSaveFullPageMethodOptions extends Omit<SaveFullPageMethodOptions, keyof WdioIcsScrollOptions>, WdioIcsScrollOptions {
}
export interface WdioCheckScreenMethodOptions extends Omit<CheckScreenMethodOptions, keyof WdioIcsCommonOptions>, WdioIcsCommonOptions {
}
export interface WdioCheckElementMethodOptions extends Omit<CheckElementMethodOptions, keyof WdioIcsCommonOptions>, WdioIcsCommonOptions {
}
export interface WdioCheckFullPageMethodOptions extends Omit<CheckFullPageMethodOptions, keyof WdioIcsScrollOptions>, WdioIcsScrollOptions {
}

export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, expectedResult?: number, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, ...args: any[]): Promise<void> {
    for (let i = 0; i < 4; i++) {
        await element.scrollIntoView();
    }
    // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
    return expect(element).toMatchElementSnapshot(tag, ...args) as unknown as Promise<void>;
}
