import { gql } from "../../__generated__";
import { simpleModelHandler } from "../base_handler";
import { extraFieldsFromYdoc, extraFieldsToYdoc } from "../extra_fields";

const GET = gql(`
    query GET_REPORT($id: bigint!) {
        report_by_pk(id: $id) {
            extraFields
        }
        extraFieldSpec(where:{targetModel:{_eq:"reporting.Report"}}){
            internalName, type
        }
    }
`);

const SET = gql(`
    mutation evi($id: bigint!, $extraFields:jsonb!) {
        update_report_by_pk(pk_columns:{id:$id}, _set:{extraFields: $extraFields}) {
            id
        }
    }
`);

const ReportHandler = simpleModelHandler(
    GET,
    SET,
    (doc, res) => {
        const obj = res.report_by_pk;
        if (!obj) throw new Error("No object");
        extraFieldsToYdoc(res.extraFieldSpec, doc, obj.extraFields);
    },
    (doc, id) => {
        const extraFields = extraFieldsFromYdoc(doc);
        return {
            id,
            extraFields,
        };
    }
);
export default ReportHandler;
