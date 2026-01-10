declare module "webdriverio" {
    interface ChainablePromiseArray {
        then: PromiseLike<WebdriverIO.ElementArray>["then"];
    }
}

export type WdioCheckElementMethodOptions = Parameters<ExpectWebdriverIO.Matchers<void, ChainablePromiseElement>["toMatchElementSnapshot"]>[1];

export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, expectedResult?: number, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, options?: WdioCheckElementMethodOptions): Promise<void>;
export async function matchElementSnapshot(element: ChainablePromiseElement, tag: string, ...args: any[]): Promise<void> {
    for (let i = 0; i < 4; i++) {
        await element.scrollIntoView();
    }
    // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
    return expect(element).toMatchElementSnapshot(tag, ...args) as unknown as Promise<void>;
}
