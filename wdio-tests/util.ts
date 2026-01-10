declare module "webdriverio" {
    interface ChainablePromiseArray {
        then: PromiseLike<WebdriverIO.ElementArray>["then"];
    }
}

export type WdioCheckElementMethodOptions = Parameters<ExpectWebdriverIO.Matchers<void, ChainablePromiseElement>["toMatchElementSnapshot"]>[1];

export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, expectedResult?: number, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, ...args: unknown[]): Promise<void> {
    for (let i = 0; i < 4; i++) {
        await element.scrollIntoView();
    }
    let i = 0;
    let expectedResult = 0.1;
    if (typeof args[i] === "number") {
        expectedResult = args[i++] as number;
    }
    let options: WdioCheckElementMethodOptions | undefined;
    if (typeof args[i] === "object") {
        options = args[i++] as WdioCheckElementMethodOptions;
    }
    return expect(element).toMatchElementSnapshot(tag, expectedResult, options) as unknown as Promise<void>;
}
