import {
    OperationVariables,
    TypedDocumentNode,
    useQuery,
} from "@apollo/client";
import * as Y from "yjs";
import { usePlainField } from "./plain_editors";

/**
 * Dropdown filled via a graphql query and read from/written to a YJS map.
 */
export default function Dropdown<
    TData,
    TVars extends OperationVariables,
>(props: {
    // YJS map that stores the value
    map: Y.Map<any>;
    // Key of the YJS map
    mapKey: string;
    // Apollo query to fetch containing the options
    optionsQuery: TypedDocumentNode<TData, TVars>;
    // Variables for the query
    optionsVars: TVars;
    // Text to use for the null value.
    unselectedText?: string;
    // Converts the graphql results to a list of `[id, option text]` tuples.
    convertOptions: (v: TData) => [number, string][];
    connected: boolean;
    // Class to apply to the select element
    className?: string;
    // ID to apply to the select element
    id?: string;
}) {
    const { data } = useQuery(props.optionsQuery, {
        variables: props.optionsVars,
        pollInterval: 10000,
    });

    const [selected, setSelected] = usePlainField<number | null>(
        props.map,
        props.mapKey,
        null
    );

    return (
        <select
            id={props.id}
            className={props.className}
            value={selected?.toString()}
            onChange={(e) => {
                setSelected(
                    e.target.value === "" ? null : parseInt(e.target.value)
                );
            }}
            disabled={!props.connected}
        >
            {props.unselectedText ? (
                <option value="">{props.unselectedText}</option>
            ) : null}
            {data
                ? props.convertOptions(data).map(([id, text]) => (
                      <option key={id} value={id}>
                          {text}
                      </option>
                  ))
                : null}
        </select>
    );
}
