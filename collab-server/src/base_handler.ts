import * as Y from "yjs";
import { ApolloClient } from "@apollo/client";

export abstract class ModelHandler {
    protected readonly client: ApolloClient<unknown>;
    protected readonly id: number;

    constructor(client: ApolloClient<unknown>, id: number) {
        this.client = client;
        this.id = id;
    }

    abstract load(): Promise<Y.Doc>;
    abstract save(doc: Y.Doc): Promise<void>;

    close(): void {}
}
