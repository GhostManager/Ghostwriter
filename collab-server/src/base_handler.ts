import * as Y from "yjs";
import { ApolloClient } from "@apollo/client";



export type ModelHandler = {
  load: (client: ApolloClient<unknown>, id: number) => Promise<Y.Doc>,
  save: (client: ApolloClient<unknown>, id: number, doc: Y.Doc) => Promise<void>,
};
