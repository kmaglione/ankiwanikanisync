import * as fs from "fs/promises";
import http from "http";
import type { AddressInfo } from "net";
import path from "node:path";

import mime from "mime";

const assetsDir = path.resolve(import.meta.dirname, "..", "dist", "assets");
const rootDir = path.resolve(import.meta.dirname, "http-root");

class Server {
    readonly #server: http.Server;
    #rootURL: string | null = null;

    get rootURL(): string | null {
        return this.#rootURL;
    }

    constructor() {
        this.#server = http.createServer((req, res) => {
            this.handleRequest(req, res).catch(error => {
                console.error(error);
                res.writeHead(500);
                res.end("500 Internal server error");
            });
        });
    }

    async handleRequest(req: http.IncomingMessage, res: http.ServerResponse<http.IncomingMessage>) {
        if (req.method !== "GET" || !req.url) {
            res.writeHead(405);
            res.end("405 Method not allowed");
            return;
        }

        const { pathname } = URL.parse(req.url, `http://${req.headers.host}/`);
        let filePath;
        if (pathname.startsWith("/assets/")) {
            filePath = path.join(assetsDir, pathname.substring("/assets/".length));
        } else {
            filePath = path.join(rootDir, pathname);
        }

        let data;
        try {
            data = await fs.readFile(filePath);
        } catch (_) {
            res.writeHead(404);
            res.end("404 Not found");
            return;
        }

        const mimeType = mime.getType(pathname);

        res.writeHead(200, { "Content-Type": mimeType });
        res.end(data);
    }

    async start() {
        await new Promise(resolve => {
            this.#server.listen(0, "localhost", () => resolve(null));
        });
        const { port } = this.#server.address() as AddressInfo;
        this.#rootURL = `http://localhost:${port}/`;
    }

    stop() {
        this.#server.close();
        this.#rootURL = null;
    }
}

export default new Server();
