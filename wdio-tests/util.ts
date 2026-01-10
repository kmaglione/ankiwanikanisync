declare module "webdriverio" {
    interface ChainablePromiseArray {
        then<U>(
            res?: ((elem: WebdriverIO.ElementArray) => Promise<U> | U) | null,
            rej?: ((val: any) => Promise<U> | U) | null
        ): Promise<U>;
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
