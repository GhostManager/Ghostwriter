import { ModelHandler } from "../base_handler";
import * as Y from "yjs";

/**
 * Handler for project tree sync documents.
 *
 * This handler is minimal - it doesn't persist any data. Its purpose is
 * to provide a shared WebSocket room for broadcasting tree change notifications
 * via stateless messages. The actual tree data comes from GraphQL queries.
 */
const ProjectTreeSyncHandler: ModelHandler<null> = {
    load: async () => [new Y.Doc(), null],
    save: async () => { /* no-op - tree sync doesn't store data */ }
};

export default ProjectTreeSyncHandler;
