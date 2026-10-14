/* eslint-disable */
/** Internal type. DO NOT USE DIRECTLY. */
type Exact<T extends { [key: string]: unknown }> = { [K in keyof T]: T[K] };
/** Internal type. DO NOT USE DIRECTLY. */
export type Incremental<T> = T | { [P in keyof T]?: P extends ' $fragmentName' | '__typename' ? T[P] : never };
import type { TypedDocumentNode as DocumentNode } from '@graphql-typed-document-node/core';
/** Boolean expression to compare columns of type "Boolean". All fields are combined with logical 'AND'. */
export type Boolean_Comparison_Exp = {
  _eq?: boolean | null | undefined;
  _gt?: boolean | null | undefined;
  _gte?: boolean | null | undefined;
  _in?: Array<boolean> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: boolean | null | undefined;
  _lte?: boolean | null | undefined;
  _neq?: boolean | null | undefined;
  _nin?: Array<boolean> | null | undefined;
};

/** Boolean expression to compare columns of type "Int". All fields are combined with logical 'AND'. */
export type Int_Comparison_Exp = {
  _eq?: number | null | undefined;
  _gt?: number | null | undefined;
  _gte?: number | null | undefined;
  _in?: Array<number> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: number | null | undefined;
  _lte?: number | null | undefined;
  _neq?: number | null | undefined;
  _nin?: Array<number> | null | undefined;
};

/** Boolean expression to compare columns of type "String". All fields are combined with logical 'AND'. */
export type String_Comparison_Exp = {
  _eq?: string | null | undefined;
  _gt?: string | null | undefined;
  _gte?: string | null | undefined;
  /** does the column match the given case-insensitive pattern */
  _ilike?: string | null | undefined;
  _in?: Array<string> | null | undefined;
  /** does the column match the given POSIX regular expression, case insensitive */
  _iregex?: string | null | undefined;
  _is_null?: boolean | null | undefined;
  /** does the column match the given pattern */
  _like?: string | null | undefined;
  _lt?: string | null | undefined;
  _lte?: string | null | undefined;
  _neq?: string | null | undefined;
  /** does the column NOT match the given case-insensitive pattern */
  _nilike?: string | null | undefined;
  _nin?: Array<string> | null | undefined;
  /** does the column NOT match the given POSIX regular expression, case insensitive */
  _niregex?: string | null | undefined;
  /** does the column NOT match the given pattern */
  _nlike?: string | null | undefined;
  /** does the column NOT match the given POSIX regular expression, case sensitive */
  _nregex?: string | null | undefined;
  /** does the column NOT match the given SQL regular expression */
  _nsimilar?: string | null | undefined;
  /** does the column match the given POSIX regular expression, case sensitive */
  _regex?: string | null | undefined;
  /** does the column match the given SQL regular expression */
  _similar?: string | null | undefined;
};

/** Boolean expression to filter rows from the table "shepherd_activitytype". All fields are combined with a logical 'AND'. */
export type ActivityType_Bool_Exp = {
  _and?: Array<ActivityType_Bool_Exp> | null | undefined;
  _not?: ActivityType_Bool_Exp | null | undefined;
  _or?: Array<ActivityType_Bool_Exp> | null | undefined;
  activity?: String_Comparison_Exp | null | undefined;
  cloudServers?: CloudServer_Bool_Exp | null | undefined;
  cloudServers_aggregate?: CloudServer_Aggregate_Bool_Exp | null | undefined;
  domains?: DomainCheckout_Bool_Exp | null | undefined;
  domains_aggregate?: DomainCheckout_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  staticServers?: ServerCheckout_Bool_Exp | null | undefined;
  staticServers_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
};

export type Archive_Aggregate_Bool_Exp = {
  count?: Archive_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Archive_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Archive_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Archive_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_archive". All fields are combined with a logical 'AND'. */
export type Archive_Bool_Exp = {
  _and?: Array<Archive_Bool_Exp> | null | undefined;
  _not?: Archive_Bool_Exp | null | undefined;
  _or?: Array<Archive_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  reportArchive?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "reporting_archive" */
export type Archive_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'projectId'
  /** column name */
  | 'reportArchive';

export type AuthPermission_Aggregate_Bool_Exp = {
  count?: AuthPermission_Aggregate_Bool_Exp_Count | null | undefined;
};

export type AuthPermission_Aggregate_Bool_Exp_Count = {
  arguments?: Array<AuthPermission_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: AuthPermission_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "auth_permission". All fields are combined with a logical 'AND'. */
export type AuthPermission_Bool_Exp = {
  _and?: Array<AuthPermission_Bool_Exp> | null | undefined;
  _not?: AuthPermission_Bool_Exp | null | undefined;
  _or?: Array<AuthPermission_Bool_Exp> | null | undefined;
  authGroupPermissions?: GroupPermission_Bool_Exp | null | undefined;
  authGroupPermissions_aggregate?: GroupPermission_Aggregate_Bool_Exp | null | undefined;
  codename?: String_Comparison_Exp | null | undefined;
  contentTypeId?: Int_Comparison_Exp | null | undefined;
  djangoContentType?: DjangoContentType_Bool_Exp | null | undefined;
  id?: Int_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  userPermissions?: UserPermission_Bool_Exp | null | undefined;
  userPermissions_aggregate?: UserPermission_Aggregate_Bool_Exp | null | undefined;
};

/** select columns of table "auth_permission" */
export type AuthPermission_Select_Column =
  /** column name */
  | 'codename'
  /** column name */
  | 'contentTypeId'
  /** column name */
  | 'id'
  /** column name */
  | 'name';

export type AuxServerAddresses_Aggregate_Bool_Exp = {
  bool_and?: AuxServerAddresses_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: AuxServerAddresses_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: AuxServerAddresses_Aggregate_Bool_Exp_Count | null | undefined;
};

export type AuxServerAddresses_Aggregate_Bool_Exp_Bool_And = {
  arguments: AuxServerAddresses_Select_Column_AuxServerAddresses_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: AuxServerAddresses_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type AuxServerAddresses_Aggregate_Bool_Exp_Bool_Or = {
  arguments: AuxServerAddresses_Select_Column_AuxServerAddresses_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: AuxServerAddresses_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type AuxServerAddresses_Aggregate_Bool_Exp_Count = {
  arguments?: Array<AuxServerAddresses_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: AuxServerAddresses_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_auxserveraddress". All fields are combined with a logical 'AND'. */
export type AuxServerAddresses_Bool_Exp = {
  _and?: Array<AuxServerAddresses_Bool_Exp> | null | undefined;
  _not?: AuxServerAddresses_Bool_Exp | null | undefined;
  _or?: Array<AuxServerAddresses_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  ipAddress?: Inet_Comparison_Exp | null | undefined;
  primary?: Boolean_Comparison_Exp | null | undefined;
  server?: StaticServer_Bool_Exp | null | undefined;
  staticServerId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "shepherd_auxserveraddress" */
export type AuxServerAddresses_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'ipAddress'
  /** column name */
  | 'primary'
  /** column name */
  | 'staticServerId';

/** select "auxServerAddresses_aggregate_bool_exp_bool_and_arguments_columns" columns of table "shepherd_auxserveraddress" */
export type AuxServerAddresses_Select_Column_AuxServerAddresses_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'primary';

/** select "auxServerAddresses_aggregate_bool_exp_bool_or_arguments_columns" columns of table "shepherd_auxserveraddress" */
export type AuxServerAddresses_Select_Column_AuxServerAddresses_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'primary';

/** Boolean expression to compare columns of type "bigint". All fields are combined with logical 'AND'. */
export type Bigint_Comparison_Exp = {
  _eq?: number | null | undefined;
  _gt?: number | null | undefined;
  _gte?: number | null | undefined;
  _in?: Array<number> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: number | null | undefined;
  _lte?: number | null | undefined;
  _neq?: number | null | undefined;
  _nin?: Array<number> | null | undefined;
};

export type ClientContact_Aggregate_Bool_Exp = {
  bool_and?: ClientContact_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ClientContact_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: ClientContact_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ClientContact_Aggregate_Bool_Exp_Bool_And = {
  arguments: ClientContact_Select_Column_ClientContact_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ClientContact_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ClientContact_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ClientContact_Select_Column_ClientContact_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ClientContact_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ClientContact_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ClientContact_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ClientContact_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_clientcontact". All fields are combined with a logical 'AND'. */
export type ClientContact_Bool_Exp = {
  _and?: Array<ClientContact_Bool_Exp> | null | undefined;
  _not?: ClientContact_Bool_Exp | null | undefined;
  _or?: Array<ClientContact_Bool_Exp> | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  email?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  jobTitle?: String_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  phone?: String_Comparison_Exp | null | undefined;
  primary?: Boolean_Comparison_Exp | null | undefined;
  timezone?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_clientcontact" */
export type ClientContact_Select_Column =
  /** column name */
  | 'clientId'
  /** column name */
  | 'description'
  /** column name */
  | 'email'
  /** column name */
  | 'id'
  /** column name */
  | 'jobTitle'
  /** column name */
  | 'name'
  /** column name */
  | 'phone'
  /** column name */
  | 'primary'
  /** column name */
  | 'timezone';

/** select "clientContact_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_clientcontact" */
export type ClientContact_Select_Column_ClientContact_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'primary';

/** select "clientContact_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_clientcontact" */
export type ClientContact_Select_Column_ClientContact_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'primary';

export type ClientInvite_Aggregate_Bool_Exp = {
  count?: ClientInvite_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ClientInvite_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ClientInvite_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ClientInvite_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_clientinvite". All fields are combined with a logical 'AND'. */
export type ClientInvite_Bool_Exp = {
  _and?: Array<ClientInvite_Bool_Exp> | null | undefined;
  _not?: ClientInvite_Bool_Exp | null | undefined;
  _or?: Array<ClientInvite_Bool_Exp> | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  comment?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  projects?: Project_Bool_Exp | null | undefined;
  projects_aggregate?: Project_Aggregate_Bool_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  userId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_clientinvite" */
export type ClientInvite_Select_Column =
  /** column name */
  | 'clientId'
  /** column name */
  | 'comment'
  /** column name */
  | 'id'
  /** column name */
  | 'userId';

export type ClientNote_Aggregate_Bool_Exp = {
  count?: ClientNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ClientNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ClientNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ClientNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_clientnote". All fields are combined with a logical 'AND'. */
export type ClientNote_Bool_Exp = {
  _and?: Array<ClientNote_Bool_Exp> | null | undefined;
  _not?: ClientNote_Bool_Exp | null | undefined;
  _or?: Array<ClientNote_Bool_Exp> | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "rolodex_clientnote" */
export type ClientNote_Select_Column =
  /** column name */
  | 'clientId'
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'timestamp';

/** Boolean expression to filter rows from the table "rolodex_client". All fields are combined with a logical 'AND'. */
export type Client_Bool_Exp = {
  _and?: Array<Client_Bool_Exp> | null | undefined;
  _not?: Client_Bool_Exp | null | undefined;
  _or?: Array<Client_Bool_Exp> | null | undefined;
  address?: String_Comparison_Exp | null | undefined;
  codename?: String_Comparison_Exp | null | undefined;
  comments?: ClientNote_Bool_Exp | null | undefined;
  comments_aggregate?: ClientNote_Aggregate_Bool_Exp | null | undefined;
  contacts?: ClientContact_Bool_Exp | null | undefined;
  contacts_aggregate?: ClientContact_Aggregate_Bool_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  domains?: DomainCheckout_Bool_Exp | null | undefined;
  domains_aggregate?: DomainCheckout_Aggregate_Bool_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  invites?: ClientInvite_Bool_Exp | null | undefined;
  invites_aggregate?: ClientInvite_Aggregate_Bool_Exp | null | undefined;
  logo?: String_Comparison_Exp | null | undefined;
  logo_height?: Int_Comparison_Exp | null | undefined;
  logo_width?: Int_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  projects?: Project_Bool_Exp | null | undefined;
  projects_aggregate?: Project_Aggregate_Bool_Exp | null | undefined;
  servers?: ServerCheckout_Bool_Exp | null | undefined;
  servers_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
  shortName?: String_Comparison_Exp | null | undefined;
  templates?: Template_Bool_Exp | null | undefined;
  templates_aggregate?: Template_Aggregate_Bool_Exp | null | undefined;
  timezone?: String_Comparison_Exp | null | undefined;
};

export type CloudServer_Aggregate_Bool_Exp = {
  count?: CloudServer_Aggregate_Bool_Exp_Count | null | undefined;
};

export type CloudServer_Aggregate_Bool_Exp_Count = {
  arguments?: Array<CloudServer_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: CloudServer_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_transientserver". All fields are combined with a logical 'AND'. */
export type CloudServer_Bool_Exp = {
  _and?: Array<CloudServer_Bool_Exp> | null | undefined;
  _not?: CloudServer_Bool_Exp | null | undefined;
  _or?: Array<CloudServer_Bool_Exp> | null | undefined;
  activityType?: ActivityType_Bool_Exp | null | undefined;
  activityTypeId?: Bigint_Comparison_Exp | null | undefined;
  auxAddress?: Inet_Array_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  domainServerConnections?: DomainServerConnection_Bool_Exp | null | undefined;
  domainServerConnections_aggregate?: DomainServerConnection_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  ipAddress?: Inet_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  serverProvider?: ServerProvider_Bool_Exp | null | undefined;
  serverProviderId?: Bigint_Comparison_Exp | null | undefined;
  serverRole?: ServerRole_Bool_Exp | null | undefined;
  serverRoleId?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_transientserver" */
export type CloudServer_Select_Column =
  /** column name */
  | 'activityTypeId'
  /** column name */
  | 'auxAddress'
  /** column name */
  | 'description'
  /** column name */
  | 'id'
  /** column name */
  | 'ipAddress'
  /** column name */
  | 'name'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'serverProviderId'
  /** column name */
  | 'serverRoleId';

/** Boolean expression to compare columns of type "date". All fields are combined with logical 'AND'. */
export type Date_Comparison_Exp = {
  _eq?: string | null | undefined;
  _gt?: string | null | undefined;
  _gte?: string | null | undefined;
  _in?: Array<string> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: string | null | undefined;
  _lte?: string | null | undefined;
  _neq?: string | null | undefined;
  _nin?: Array<string> | null | undefined;
};

/** Boolean expression to filter rows from the table "rolodex_deconflictionstatus". All fields are combined with a logical 'AND'. */
export type DeconflictionStatus_Bool_Exp = {
  _and?: Array<DeconflictionStatus_Bool_Exp> | null | undefined;
  _not?: DeconflictionStatus_Bool_Exp | null | undefined;
  _or?: Array<DeconflictionStatus_Bool_Exp> | null | undefined;
  deconflictions?: Deconfliction_Bool_Exp | null | undefined;
  deconflictions_aggregate?: Deconfliction_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  status?: String_Comparison_Exp | null | undefined;
  weight?: Int_Comparison_Exp | null | undefined;
};

export type Deconfliction_Aggregate_Bool_Exp = {
  count?: Deconfliction_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Deconfliction_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Deconfliction_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Deconfliction_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_deconfliction". All fields are combined with a logical 'AND'. */
export type Deconfliction_Bool_Exp = {
  _and?: Array<Deconfliction_Bool_Exp> | null | undefined;
  _not?: Deconfliction_Bool_Exp | null | undefined;
  _or?: Array<Deconfliction_Bool_Exp> | null | undefined;
  alertSource?: String_Comparison_Exp | null | undefined;
  alertTimestamp?: Timestamptz_Comparison_Exp | null | undefined;
  createdAt?: Timestamptz_Comparison_Exp | null | undefined;
  deconflictionStatus?: DeconflictionStatus_Bool_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  reportTimestamp?: Timestamptz_Comparison_Exp | null | undefined;
  responseTimestamp?: Timestamptz_Comparison_Exp | null | undefined;
  statusId?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_deconfliction" */
export type Deconfliction_Select_Column =
  /** column name */
  | 'alertSource'
  /** column name */
  | 'alertTimestamp'
  /** column name */
  | 'createdAt'
  /** column name */
  | 'description'
  /** column name */
  | 'id'
  /** column name */
  | 'projectId'
  /** column name */
  | 'reportTimestamp'
  /** column name */
  | 'responseTimestamp'
  /** column name */
  | 'statusId'
  /** column name */
  | 'title';

/** Boolean expression to filter rows from the table "django_content_type". All fields are combined with a logical 'AND'. */
export type DjangoContentType_Bool_Exp = {
  _and?: Array<DjangoContentType_Bool_Exp> | null | undefined;
  _not?: DjangoContentType_Bool_Exp | null | undefined;
  _or?: Array<DjangoContentType_Bool_Exp> | null | undefined;
  appLabel?: String_Comparison_Exp | null | undefined;
  authPermissions?: AuthPermission_Bool_Exp | null | undefined;
  authPermissions_aggregate?: AuthPermission_Aggregate_Bool_Exp | null | undefined;
  id?: Int_Comparison_Exp | null | undefined;
  model?: String_Comparison_Exp | null | undefined;
  tags?: TaggedItem_Bool_Exp | null | undefined;
  tags_aggregate?: TaggedItem_Aggregate_Bool_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "reporting_doctype". All fields are combined with a logical 'AND'. */
export type DocType_Bool_Exp = {
  _and?: Array<DocType_Bool_Exp> | null | undefined;
  _not?: DocType_Bool_Exp | null | undefined;
  _or?: Array<DocType_Bool_Exp> | null | undefined;
  docType?: String_Comparison_Exp | null | undefined;
  extension?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  templates?: Template_Bool_Exp | null | undefined;
  templates_aggregate?: Template_Aggregate_Bool_Exp | null | undefined;
};

export type DomainCheckout_Aggregate_Bool_Exp = {
  count?: DomainCheckout_Aggregate_Bool_Exp_Count | null | undefined;
};

export type DomainCheckout_Aggregate_Bool_Exp_Count = {
  arguments?: Array<DomainCheckout_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: DomainCheckout_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_history". All fields are combined with a logical 'AND'. */
export type DomainCheckout_Bool_Exp = {
  _and?: Array<DomainCheckout_Bool_Exp> | null | undefined;
  _not?: DomainCheckout_Bool_Exp | null | undefined;
  _or?: Array<DomainCheckout_Bool_Exp> | null | undefined;
  activityType?: ActivityType_Bool_Exp | null | undefined;
  activityTypeId?: Bigint_Comparison_Exp | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  domain?: Domain_Bool_Exp | null | undefined;
  domainId?: Bigint_Comparison_Exp | null | undefined;
  domainServerConnections?: DomainServerConnection_Bool_Exp | null | undefined;
  domainServerConnections_aggregate?: DomainServerConnection_Aggregate_Bool_Exp | null | undefined;
  endDate?: Date_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  startDate?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_history" */
export type DomainCheckout_Select_Column =
  /** column name */
  | 'activityTypeId'
  /** column name */
  | 'clientId'
  /** column name */
  | 'description'
  /** column name */
  | 'domainId'
  /** column name */
  | 'endDate'
  /** column name */
  | 'id'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'startDate';

export type DomainNote_Aggregate_Bool_Exp = {
  count?: DomainNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type DomainNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<DomainNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: DomainNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_domainnote". All fields are combined with a logical 'AND'. */
export type DomainNote_Bool_Exp = {
  _and?: Array<DomainNote_Bool_Exp> | null | undefined;
  _not?: DomainNote_Bool_Exp | null | undefined;
  _or?: Array<DomainNote_Bool_Exp> | null | undefined;
  domain?: Domain_Bool_Exp | null | undefined;
  domainId?: Bigint_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_domainnote" */
export type DomainNote_Select_Column =
  /** column name */
  | 'domainId'
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'timestamp';

export type DomainServerConnection_Aggregate_Bool_Exp = {
  count?: DomainServerConnection_Aggregate_Bool_Exp_Count | null | undefined;
};

export type DomainServerConnection_Aggregate_Bool_Exp_Count = {
  arguments?: Array<DomainServerConnection_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: DomainServerConnection_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_domainserverconnection". All fields are combined with a logical 'AND'. */
export type DomainServerConnection_Bool_Exp = {
  _and?: Array<DomainServerConnection_Bool_Exp> | null | undefined;
  _not?: DomainServerConnection_Bool_Exp | null | undefined;
  _or?: Array<DomainServerConnection_Bool_Exp> | null | undefined;
  cloudServer?: CloudServer_Bool_Exp | null | undefined;
  domain?: DomainCheckout_Bool_Exp | null | undefined;
  domainId?: Bigint_Comparison_Exp | null | undefined;
  endpoint?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  staticServer?: ServerCheckout_Bool_Exp | null | undefined;
  staticServerId?: Bigint_Comparison_Exp | null | undefined;
  subdomain?: String_Comparison_Exp | null | undefined;
  transientServerId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "shepherd_domainserverconnection" */
export type DomainServerConnection_Select_Column =
  /** column name */
  | 'domainId'
  /** column name */
  | 'endpoint'
  /** column name */
  | 'id'
  /** column name */
  | 'projectId'
  /** column name */
  | 'staticServerId'
  /** column name */
  | 'subdomain'
  /** column name */
  | 'transientServerId';

/** Boolean expression to filter rows from the table "shepherd_domainstatus". All fields are combined with a logical 'AND'. */
export type DomainStatus_Bool_Exp = {
  _and?: Array<DomainStatus_Bool_Exp> | null | undefined;
  _not?: DomainStatus_Bool_Exp | null | undefined;
  _or?: Array<DomainStatus_Bool_Exp> | null | undefined;
  domainStatus?: String_Comparison_Exp | null | undefined;
  domains?: Domain_Bool_Exp | null | undefined;
  domains_aggregate?: Domain_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
};

export type Domain_Aggregate_Bool_Exp = {
  bool_and?: Domain_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Domain_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Domain_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Domain_Aggregate_Bool_Exp_Bool_And = {
  arguments: Domain_Select_Column_Domain_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Domain_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Domain_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Domain_Select_Column_Domain_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Domain_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Domain_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Domain_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Domain_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_domain". All fields are combined with a logical 'AND'. */
export type Domain_Bool_Exp = {
  _and?: Array<Domain_Bool_Exp> | null | undefined;
  _not?: Domain_Bool_Exp | null | undefined;
  _or?: Array<Domain_Bool_Exp> | null | undefined;
  autoRenew?: Boolean_Comparison_Exp | null | undefined;
  burned_explanation?: String_Comparison_Exp | null | undefined;
  categorization?: Jsonb_Comparison_Exp | null | undefined;
  checkouts?: DomainCheckout_Bool_Exp | null | undefined;
  checkouts_aggregate?: DomainCheckout_Aggregate_Bool_Exp | null | undefined;
  comments?: DomainNote_Bool_Exp | null | undefined;
  comments_aggregate?: DomainNote_Aggregate_Bool_Exp | null | undefined;
  creation?: Date_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  dns?: Jsonb_Comparison_Exp | null | undefined;
  domainStatus?: DomainStatus_Bool_Exp | null | undefined;
  domainStatusId?: Bigint_Comparison_Exp | null | undefined;
  expiration?: Date_Comparison_Exp | null | undefined;
  expired?: Boolean_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  healthStatus?: HealthStatus_Bool_Exp | null | undefined;
  healthStatusId?: Bigint_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  lastHealthCheck?: Date_Comparison_Exp | null | undefined;
  lastUsedById?: Bigint_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  registrar?: String_Comparison_Exp | null | undefined;
  resetDns?: Boolean_Comparison_Exp | null | undefined;
  serviceTokenDomainAccesses?: ServiceTokenDomainAccess_Bool_Exp | null | undefined;
  serviceTokenDomainAccesses_aggregate?: ServiceTokenDomainAccess_Aggregate_Bool_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  vtPermalink?: String_Comparison_Exp | null | undefined;
  whoisStatus?: WhoisStatus_Bool_Exp | null | undefined;
  whoisStatusId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "shepherd_domain" */
export type Domain_Select_Column =
  /** column name */
  | 'autoRenew'
  /** column name */
  | 'burned_explanation'
  /** column name */
  | 'categorization'
  /** column name */
  | 'creation'
  /** column name */
  | 'description'
  /** column name */
  | 'dns'
  /** column name */
  | 'domainStatusId'
  /** column name */
  | 'expiration'
  /** column name */
  | 'expired'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'healthStatusId'
  /** column name */
  | 'id'
  /** column name */
  | 'lastHealthCheck'
  /** column name */
  | 'lastUsedById'
  /** column name */
  | 'name'
  /** column name */
  | 'registrar'
  /** column name */
  | 'resetDns'
  /** column name */
  | 'vtPermalink'
  /** column name */
  | 'whoisStatusId';

/** select "domain_aggregate_bool_exp_bool_and_arguments_columns" columns of table "shepherd_domain" */
export type Domain_Select_Column_Domain_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'autoRenew'
  /** column name */
  | 'expired'
  /** column name */
  | 'resetDns';

/** select "domain_aggregate_bool_exp_bool_or_arguments_columns" columns of table "shepherd_domain" */
export type Domain_Select_Column_Domain_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'autoRenew'
  /** column name */
  | 'expired'
  /** column name */
  | 'resetDns';

export type Evidence_Aggregate_Bool_Exp = {
  count?: Evidence_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Evidence_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Evidence_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Evidence_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_evidence". All fields are combined with a logical 'AND'. */
export type Evidence_Bool_Exp = {
  _and?: Array<Evidence_Bool_Exp> | null | undefined;
  _not?: Evidence_Bool_Exp | null | undefined;
  _or?: Array<Evidence_Bool_Exp> | null | undefined;
  caption?: String_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  document?: String_Comparison_Exp | null | undefined;
  friendlyName?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  report?: Report_Bool_Exp | null | undefined;
  reportId?: Bigint_Comparison_Exp | null | undefined;
  uploadDate?: Date_Comparison_Exp | null | undefined;
  uploadedById?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_evidence" */
export type Evidence_Select_Column =
  /** column name */
  | 'caption'
  /** column name */
  | 'description'
  /** column name */
  | 'document'
  /** column name */
  | 'friendlyName'
  /** column name */
  | 'id'
  /** column name */
  | 'reportId'
  /** column name */
  | 'uploadDate'
  /** column name */
  | 'uploadedById';

export type FindingNote_Aggregate_Bool_Exp = {
  count?: FindingNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type FindingNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<FindingNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: FindingNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_findingnote". All fields are combined with a logical 'AND'. */
export type FindingNote_Bool_Exp = {
  _and?: Array<FindingNote_Bool_Exp> | null | undefined;
  _not?: FindingNote_Bool_Exp | null | undefined;
  _or?: Array<FindingNote_Bool_Exp> | null | undefined;
  finding?: Finding_Bool_Exp | null | undefined;
  findingId?: Bigint_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_findingnote" */
export type FindingNote_Select_Column =
  /** column name */
  | 'findingId'
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'timestamp';

/** Boolean expression to filter rows from the table "reporting_severity". All fields are combined with a logical 'AND'. */
export type FindingSeverity_Bool_Exp = {
  _and?: Array<FindingSeverity_Bool_Exp> | null | undefined;
  _not?: FindingSeverity_Bool_Exp | null | undefined;
  _or?: Array<FindingSeverity_Bool_Exp> | null | undefined;
  color?: String_Comparison_Exp | null | undefined;
  findings?: Finding_Bool_Exp | null | undefined;
  findings_aggregate?: Finding_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  reportedFindings?: ReportedFinding_Bool_Exp | null | undefined;
  reportedFindings_aggregate?: ReportedFinding_Aggregate_Bool_Exp | null | undefined;
  severity?: String_Comparison_Exp | null | undefined;
  weight?: Int_Comparison_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "reporting_findingtype". All fields are combined with a logical 'AND'. */
export type FindingType_Bool_Exp = {
  _and?: Array<FindingType_Bool_Exp> | null | undefined;
  _not?: FindingType_Bool_Exp | null | undefined;
  _or?: Array<FindingType_Bool_Exp> | null | undefined;
  findingType?: String_Comparison_Exp | null | undefined;
  findings?: Finding_Bool_Exp | null | undefined;
  findings_aggregate?: Finding_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  reportedFindings?: ReportedFinding_Bool_Exp | null | undefined;
  reportedFindings_aggregate?: ReportedFinding_Aggregate_Bool_Exp | null | undefined;
};

export type Finding_Aggregate_Bool_Exp = {
  avg?: Finding_Aggregate_Bool_Exp_Avg | null | undefined;
  corr?: Finding_Aggregate_Bool_Exp_Corr | null | undefined;
  count?: Finding_Aggregate_Bool_Exp_Count | null | undefined;
  covar_samp?: Finding_Aggregate_Bool_Exp_Covar_Samp | null | undefined;
  max?: Finding_Aggregate_Bool_Exp_Max | null | undefined;
  min?: Finding_Aggregate_Bool_Exp_Min | null | undefined;
  stddev_samp?: Finding_Aggregate_Bool_Exp_Stddev_Samp | null | undefined;
  sum?: Finding_Aggregate_Bool_Exp_Sum | null | undefined;
  var_samp?: Finding_Aggregate_Bool_Exp_Var_Samp | null | undefined;
};

export type Finding_Aggregate_Bool_Exp_Avg = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Avg_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Corr = {
  arguments: Finding_Aggregate_Bool_Exp_Corr_Arguments;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Corr_Arguments = {
  X: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Corr_Arguments_Columns;
  Y: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Corr_Arguments_Columns;
};

export type Finding_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Finding_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Covar_Samp = {
  arguments: Finding_Aggregate_Bool_Exp_Covar_Samp_Arguments;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Covar_Samp_Arguments = {
  X: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
  Y: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
};

export type Finding_Aggregate_Bool_Exp_Max = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Max_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Min = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Min_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Stddev_Samp = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Sum = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Sum_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Finding_Aggregate_Bool_Exp_Var_Samp = {
  arguments: Finding_Select_Column_Finding_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Finding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_finding". All fields are combined with a logical 'AND'. */
export type Finding_Bool_Exp = {
  _and?: Array<Finding_Bool_Exp> | null | undefined;
  _not?: Finding_Bool_Exp | null | undefined;
  _or?: Array<Finding_Bool_Exp> | null | undefined;
  comments?: FindingNote_Bool_Exp | null | undefined;
  comments_aggregate?: FindingNote_Aggregate_Bool_Exp | null | undefined;
  cvssScore?: Float8_Comparison_Exp | null | undefined;
  cvssVector?: String_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  findingGuidance?: String_Comparison_Exp | null | undefined;
  findingTypeId?: Bigint_Comparison_Exp | null | undefined;
  hostDetectionTechniques?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  impact?: String_Comparison_Exp | null | undefined;
  mitigation?: String_Comparison_Exp | null | undefined;
  networkDetectionTechniques?: String_Comparison_Exp | null | undefined;
  references?: String_Comparison_Exp | null | undefined;
  replication_steps?: String_Comparison_Exp | null | undefined;
  severity?: FindingSeverity_Bool_Exp | null | undefined;
  severityId?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
  type?: FindingType_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_finding" */
export type Finding_Select_Column =
  /** column name */
  | 'cvssScore'
  /** column name */
  | 'cvssVector'
  /** column name */
  | 'description'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'findingGuidance'
  /** column name */
  | 'findingTypeId'
  /** column name */
  | 'hostDetectionTechniques'
  /** column name */
  | 'id'
  /** column name */
  | 'impact'
  /** column name */
  | 'mitigation'
  /** column name */
  | 'networkDetectionTechniques'
  /** column name */
  | 'references'
  /** column name */
  | 'replication_steps'
  /** column name */
  | 'severityId'
  /** column name */
  | 'title';

/** select "finding_aggregate_bool_exp_avg_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Avg_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_corr_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Corr_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_covar_samp_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_max_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Max_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_min_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Min_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_stddev_samp_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_sum_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Sum_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "finding_aggregate_bool_exp_var_samp_arguments_columns" columns of table "reporting_finding" */
export type Finding_Select_Column_Finding_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** input type for updating data in table "reporting_finding" */
export type Finding_Set_Input = {
  cvssScore?: number | null | undefined;
  cvssVector?: string | null | undefined;
  description?: string | null | undefined;
  extraFields?: Record<string, unknown> | null | undefined;
  findingGuidance?: string | null | undefined;
  findingTypeId?: number | null | undefined;
  hostDetectionTechniques?: string | null | undefined;
  id?: number | null | undefined;
  impact?: string | null | undefined;
  mitigation?: string | null | undefined;
  networkDetectionTechniques?: string | null | undefined;
  references?: string | null | undefined;
  replication_steps?: string | null | undefined;
  severityId?: number | null | undefined;
  title?: string | null | undefined;
};

/** Boolean expression to compare columns of type "float8". All fields are combined with logical 'AND'. */
export type Float8_Comparison_Exp = {
  _eq?: number | null | undefined;
  _gt?: number | null | undefined;
  _gte?: number | null | undefined;
  _in?: Array<number> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: number | null | undefined;
  _lte?: number | null | undefined;
  _neq?: number | null | undefined;
  _nin?: Array<number> | null | undefined;
};

export type GroupPermission_Aggregate_Bool_Exp = {
  count?: GroupPermission_Aggregate_Bool_Exp_Count | null | undefined;
};

export type GroupPermission_Aggregate_Bool_Exp_Count = {
  arguments?: Array<GroupPermission_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: GroupPermission_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "auth_group_permissions". All fields are combined with a logical 'AND'. */
export type GroupPermission_Bool_Exp = {
  _and?: Array<GroupPermission_Bool_Exp> | null | undefined;
  _not?: GroupPermission_Bool_Exp | null | undefined;
  _or?: Array<GroupPermission_Bool_Exp> | null | undefined;
  authGroup?: Group_Bool_Exp | null | undefined;
  authPermission?: AuthPermission_Bool_Exp | null | undefined;
  groupId?: Int_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  permissionId?: Int_Comparison_Exp | null | undefined;
};

/** select columns of table "auth_group_permissions" */
export type GroupPermission_Select_Column =
  /** column name */
  | 'groupId'
  /** column name */
  | 'id'
  /** column name */
  | 'permissionId';

/** Boolean expression to filter rows from the table "auth_group". All fields are combined with a logical 'AND'. */
export type Group_Bool_Exp = {
  _and?: Array<Group_Bool_Exp> | null | undefined;
  _not?: Group_Bool_Exp | null | undefined;
  _or?: Array<Group_Bool_Exp> | null | undefined;
  groupPermissions?: GroupPermission_Bool_Exp | null | undefined;
  groupPermissions_aggregate?: GroupPermission_Aggregate_Bool_Exp | null | undefined;
  id?: Int_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  users?: UserGroup_Bool_Exp | null | undefined;
  users_aggregate?: UserGroup_Aggregate_Bool_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "shepherd_healthstatus". All fields are combined with a logical 'AND'. */
export type HealthStatus_Bool_Exp = {
  _and?: Array<HealthStatus_Bool_Exp> | null | undefined;
  _not?: HealthStatus_Bool_Exp | null | undefined;
  _or?: Array<HealthStatus_Bool_Exp> | null | undefined;
  domains?: Domain_Bool_Exp | null | undefined;
  domains_aggregate?: Domain_Aggregate_Bool_Exp | null | undefined;
  healthStatus?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
};

/** Boolean expression to compare columns of type "inet". All fields are combined with logical 'AND'. */
export type Inet_Array_Comparison_Exp = {
  /** is the array contained in the given array value */
  _contained_in?: Array<string> | null | undefined;
  /** does the array contain the given value */
  _contains?: Array<string> | null | undefined;
  _eq?: Array<string> | null | undefined;
  _gt?: Array<string> | null | undefined;
  _gte?: Array<string> | null | undefined;
  _in?: Array<Array<string>> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: Array<string> | null | undefined;
  _lte?: Array<string> | null | undefined;
  _neq?: Array<string> | null | undefined;
  _nin?: Array<Array<string>> | null | undefined;
};

/** Boolean expression to compare columns of type "inet". All fields are combined with logical 'AND'. */
export type Inet_Comparison_Exp = {
  _eq?: string | null | undefined;
  _gt?: string | null | undefined;
  _gte?: string | null | undefined;
  _in?: Array<string> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: string | null | undefined;
  _lte?: string | null | undefined;
  _neq?: string | null | undefined;
  _nin?: Array<string> | null | undefined;
};

export type Jsonb_Cast_Exp = {
  String?: String_Comparison_Exp | null | undefined;
};

/** Boolean expression to compare columns of type "jsonb". All fields are combined with logical 'AND'. */
export type Jsonb_Comparison_Exp = {
  _cast?: Jsonb_Cast_Exp | null | undefined;
  /** is the column contained in the given json value */
  _contained_in?: Record<string, unknown> | null | undefined;
  /** does the column contain the given json value at the top level */
  _contains?: Record<string, unknown> | null | undefined;
  _eq?: Record<string, unknown> | null | undefined;
  _gt?: Record<string, unknown> | null | undefined;
  _gte?: Record<string, unknown> | null | undefined;
  /** does the string exist as a top-level key in the column */
  _has_key?: string | null | undefined;
  /** do all of these strings exist as top-level keys in the column */
  _has_keys_all?: Array<string> | null | undefined;
  /** do any of these strings exist as top-level keys in the column */
  _has_keys_any?: Array<string> | null | undefined;
  _in?: Array<Record<string, unknown>> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: Record<string, unknown> | null | undefined;
  _lte?: Record<string, unknown> | null | undefined;
  _neq?: Record<string, unknown> | null | undefined;
  _nin?: Array<Record<string, unknown>> | null | undefined;
};

/** Boolean expression to filter rows from the table "rolodex_objectivepriority". All fields are combined with a logical 'AND'. */
export type ObjectivePriority_Bool_Exp = {
  _and?: Array<ObjectivePriority_Bool_Exp> | null | undefined;
  _not?: ObjectivePriority_Bool_Exp | null | undefined;
  _or?: Array<ObjectivePriority_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  objectives?: Objective_Bool_Exp | null | undefined;
  objectives_aggregate?: Objective_Aggregate_Bool_Exp | null | undefined;
  priority?: String_Comparison_Exp | null | undefined;
  weight?: Int_Comparison_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "rolodex_objectivestatus". All fields are combined with a logical 'AND'. */
export type ObjectiveStatus_Bool_Exp = {
  _and?: Array<ObjectiveStatus_Bool_Exp> | null | undefined;
  _not?: ObjectiveStatus_Bool_Exp | null | undefined;
  _or?: Array<ObjectiveStatus_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  objectiveStatus?: String_Comparison_Exp | null | undefined;
  objectiveSubTasks?: ObjectiveSubTask_Bool_Exp | null | undefined;
  objectiveSubTasks_aggregate?: ObjectiveSubTask_Aggregate_Bool_Exp | null | undefined;
  objectives?: Objective_Bool_Exp | null | undefined;
  objectives_aggregate?: Objective_Aggregate_Bool_Exp | null | undefined;
};

export type ObjectiveSubTask_Aggregate_Bool_Exp = {
  bool_and?: ObjectiveSubTask_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ObjectiveSubTask_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: ObjectiveSubTask_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ObjectiveSubTask_Aggregate_Bool_Exp_Bool_And = {
  arguments: ObjectiveSubTask_Select_Column_ObjectiveSubTask_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ObjectiveSubTask_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ObjectiveSubTask_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ObjectiveSubTask_Select_Column_ObjectiveSubTask_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ObjectiveSubTask_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ObjectiveSubTask_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ObjectiveSubTask_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ObjectiveSubTask_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectsubtask". All fields are combined with a logical 'AND'. */
export type ObjectiveSubTask_Bool_Exp = {
  _and?: Array<ObjectiveSubTask_Bool_Exp> | null | undefined;
  _not?: ObjectiveSubTask_Bool_Exp | null | undefined;
  _or?: Array<ObjectiveSubTask_Bool_Exp> | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  deadline?: Date_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  markedComplete?: Date_Comparison_Exp | null | undefined;
  objective?: Objective_Bool_Exp | null | undefined;
  objectiveStatus?: ObjectiveStatus_Bool_Exp | null | undefined;
  parentId?: Bigint_Comparison_Exp | null | undefined;
  statusId?: Bigint_Comparison_Exp | null | undefined;
  task?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projectsubtask" */
export type ObjectiveSubTask_Select_Column =
  /** column name */
  | 'complete'
  /** column name */
  | 'deadline'
  /** column name */
  | 'id'
  /** column name */
  | 'markedComplete'
  /** column name */
  | 'parentId'
  /** column name */
  | 'statusId'
  /** column name */
  | 'task';

/** select "objectiveSubTask_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_projectsubtask" */
export type ObjectiveSubTask_Select_Column_ObjectiveSubTask_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'complete';

/** select "objectiveSubTask_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_projectsubtask" */
export type ObjectiveSubTask_Select_Column_ObjectiveSubTask_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'complete';

export type Objective_Aggregate_Bool_Exp = {
  bool_and?: Objective_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Objective_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Objective_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Objective_Aggregate_Bool_Exp_Bool_And = {
  arguments: Objective_Select_Column_Objective_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Objective_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Objective_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Objective_Select_Column_Objective_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Objective_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Objective_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Objective_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Objective_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectobjective". All fields are combined with a logical 'AND'. */
export type Objective_Bool_Exp = {
  _and?: Array<Objective_Bool_Exp> | null | undefined;
  _not?: Objective_Bool_Exp | null | undefined;
  _or?: Array<Objective_Bool_Exp> | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  deadline?: Date_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  markedComplete?: Date_Comparison_Exp | null | undefined;
  objective?: String_Comparison_Exp | null | undefined;
  objectivePriority?: ObjectivePriority_Bool_Exp | null | undefined;
  objectiveStatus?: ObjectiveStatus_Bool_Exp | null | undefined;
  objectiveSubTasks?: ObjectiveSubTask_Bool_Exp | null | undefined;
  objectiveSubTasks_aggregate?: ObjectiveSubTask_Aggregate_Bool_Exp | null | undefined;
  position?: Int_Comparison_Exp | null | undefined;
  priorityId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  result?: String_Comparison_Exp | null | undefined;
  statusId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projectobjective" */
export type Objective_Select_Column =
  /** column name */
  | 'complete'
  /** column name */
  | 'deadline'
  /** column name */
  | 'description'
  /** column name */
  | 'id'
  /** column name */
  | 'markedComplete'
  /** column name */
  | 'objective'
  /** column name */
  | 'position'
  /** column name */
  | 'priorityId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'result'
  /** column name */
  | 'statusId';

/** select "objective_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_projectobjective" */
export type Objective_Select_Column_Objective_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'complete';

/** select "objective_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_projectobjective" */
export type Objective_Select_Column_Objective_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'complete';

export type OplogEntry_Aggregate_Bool_Exp = {
  count?: OplogEntry_Aggregate_Bool_Exp_Count | null | undefined;
};

export type OplogEntry_Aggregate_Bool_Exp_Count = {
  arguments?: Array<OplogEntry_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: OplogEntry_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "oplog_oplogentry". All fields are combined with a logical 'AND'. */
export type OplogEntry_Bool_Exp = {
  _and?: Array<OplogEntry_Bool_Exp> | null | undefined;
  _not?: OplogEntry_Bool_Exp | null | undefined;
  _or?: Array<OplogEntry_Bool_Exp> | null | undefined;
  command?: String_Comparison_Exp | null | undefined;
  comments?: String_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  destIp?: String_Comparison_Exp | null | undefined;
  endDate?: Timestamptz_Comparison_Exp | null | undefined;
  entryIdentifier?: String_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  log?: Oplog_Bool_Exp | null | undefined;
  operatorName?: String_Comparison_Exp | null | undefined;
  oplog?: Bigint_Comparison_Exp | null | undefined;
  output?: String_Comparison_Exp | null | undefined;
  sourceIp?: String_Comparison_Exp | null | undefined;
  startDate?: Timestamptz_Comparison_Exp | null | undefined;
  tool?: String_Comparison_Exp | null | undefined;
  updatedAt?: Timestamptz_Comparison_Exp | null | undefined;
  userContext?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "oplog_oplogentry" */
export type OplogEntry_Select_Column =
  /** column name */
  | 'command'
  /** column name */
  | 'comments'
  /** column name */
  | 'description'
  /** column name */
  | 'destIp'
  /** column name */
  | 'endDate'
  /** column name */
  | 'entryIdentifier'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'id'
  /** column name */
  | 'operatorName'
  /** column name */
  | 'oplog'
  /** column name */
  | 'output'
  /** column name */
  | 'sourceIp'
  /** column name */
  | 'startDate'
  /** column name */
  | 'tool'
  /** column name */
  | 'updatedAt'
  /** column name */
  | 'userContext';

export type OplogSanitization_Aggregate_Bool_Exp = {
  count?: OplogSanitization_Aggregate_Bool_Exp_Count | null | undefined;
};

export type OplogSanitization_Aggregate_Bool_Exp_Count = {
  arguments?: Array<OplogSanitization_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: OplogSanitization_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "oplog_oplogsanitization". All fields are combined with a logical 'AND'. */
export type OplogSanitization_Bool_Exp = {
  _and?: Array<OplogSanitization_Bool_Exp> | null | undefined;
  _not?: OplogSanitization_Bool_Exp | null | undefined;
  _or?: Array<OplogSanitization_Bool_Exp> | null | undefined;
  fields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  oplog?: Oplog_Bool_Exp | null | undefined;
  oplogId?: Bigint_Comparison_Exp | null | undefined;
  sanitizedAt?: Timestamptz_Comparison_Exp | null | undefined;
  sanitizedBy?: User_Bool_Exp | null | undefined;
  sanitizedById?: Bigint_Comparison_Exp | null | undefined;
  sanitizedByName?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "oplog_oplogsanitization" */
export type OplogSanitization_Select_Column =
  /** column name */
  | 'fields'
  /** column name */
  | 'id'
  /** column name */
  | 'oplogId'
  /** column name */
  | 'sanitizedAt'
  /** column name */
  | 'sanitizedById'
  /** column name */
  | 'sanitizedByName';

export type Oplog_Aggregate_Bool_Exp = {
  bool_and?: Oplog_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Oplog_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Oplog_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Oplog_Aggregate_Bool_Exp_Bool_And = {
  arguments: Oplog_Select_Column_Oplog_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Oplog_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Oplog_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Oplog_Select_Column_Oplog_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Oplog_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Oplog_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Oplog_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Oplog_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "oplog_oplog". All fields are combined with a logical 'AND'. */
export type Oplog_Bool_Exp = {
  _and?: Array<Oplog_Bool_Exp> | null | undefined;
  _not?: Oplog_Bool_Exp | null | undefined;
  _or?: Array<Oplog_Bool_Exp> | null | undefined;
  entries?: OplogEntry_Bool_Exp | null | undefined;
  entries_aggregate?: OplogEntry_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  mute_notifications?: Boolean_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  sanitizations?: OplogSanitization_Bool_Exp | null | undefined;
  sanitizations_aggregate?: OplogSanitization_Aggregate_Bool_Exp | null | undefined;
};

/** select columns of table "oplog_oplog" */
export type Oplog_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'mute_notifications'
  /** column name */
  | 'name'
  /** column name */
  | 'projectId';

/** select "oplog_aggregate_bool_exp_bool_and_arguments_columns" columns of table "oplog_oplog" */
export type Oplog_Select_Column_Oplog_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'mute_notifications';

/** select "oplog_aggregate_bool_exp_bool_or_arguments_columns" columns of table "oplog_oplog" */
export type Oplog_Select_Column_Oplog_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'mute_notifications';

export type ProjectAssignment_Aggregate_Bool_Exp = {
  count?: ProjectAssignment_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ProjectAssignment_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ProjectAssignment_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ProjectAssignment_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectassignment". All fields are combined with a logical 'AND'. */
export type ProjectAssignment_Bool_Exp = {
  _and?: Array<ProjectAssignment_Bool_Exp> | null | undefined;
  _not?: ProjectAssignment_Bool_Exp | null | undefined;
  _or?: Array<ProjectAssignment_Bool_Exp> | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  endDate?: Date_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  projectRole?: ProjectRole_Bool_Exp | null | undefined;
  roleId?: Bigint_Comparison_Exp | null | undefined;
  startDate?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "rolodex_projectassignment" */
export type ProjectAssignment_Select_Column =
  /** column name */
  | 'description'
  /** column name */
  | 'endDate'
  /** column name */
  | 'id'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'roleId'
  /** column name */
  | 'startDate';

export type ProjectContact_Aggregate_Bool_Exp = {
  bool_and?: ProjectContact_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ProjectContact_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: ProjectContact_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ProjectContact_Aggregate_Bool_Exp_Bool_And = {
  arguments: ProjectContact_Select_Column_ProjectContact_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ProjectContact_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ProjectContact_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ProjectContact_Select_Column_ProjectContact_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ProjectContact_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ProjectContact_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ProjectContact_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ProjectContact_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectcontact". All fields are combined with a logical 'AND'. */
export type ProjectContact_Bool_Exp = {
  _and?: Array<ProjectContact_Bool_Exp> | null | undefined;
  _not?: ProjectContact_Bool_Exp | null | undefined;
  _or?: Array<ProjectContact_Bool_Exp> | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  email?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  job_title?: String_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  phone?: String_Comparison_Exp | null | undefined;
  primary?: Boolean_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  timezone?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projectcontact" */
export type ProjectContact_Select_Column =
  /** column name */
  | 'description'
  /** column name */
  | 'email'
  /** column name */
  | 'id'
  /** column name */
  | 'job_title'
  /** column name */
  | 'name'
  /** column name */
  | 'phone'
  /** column name */
  | 'primary'
  /** column name */
  | 'projectId'
  /** column name */
  | 'timezone';

/** select "projectContact_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_projectcontact" */
export type ProjectContact_Select_Column_ProjectContact_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'primary';

/** select "projectContact_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_projectcontact" */
export type ProjectContact_Select_Column_ProjectContact_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'primary';

export type ProjectInvite_Aggregate_Bool_Exp = {
  count?: ProjectInvite_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ProjectInvite_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ProjectInvite_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ProjectInvite_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectinvite". All fields are combined with a logical 'AND'. */
export type ProjectInvite_Bool_Exp = {
  _and?: Array<ProjectInvite_Bool_Exp> | null | undefined;
  _not?: ProjectInvite_Bool_Exp | null | undefined;
  _or?: Array<ProjectInvite_Bool_Exp> | null | undefined;
  assignments?: ProjectAssignment_Bool_Exp | null | undefined;
  assignments_aggregate?: ProjectAssignment_Aggregate_Bool_Exp | null | undefined;
  comment?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  userId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projectinvite" */
export type ProjectInvite_Select_Column =
  /** column name */
  | 'comment'
  /** column name */
  | 'id'
  /** column name */
  | 'projectId'
  /** column name */
  | 'userId';

export type ProjectNote_Aggregate_Bool_Exp = {
  count?: ProjectNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ProjectNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ProjectNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ProjectNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectnote". All fields are combined with a logical 'AND'. */
export type ProjectNote_Bool_Exp = {
  _and?: Array<ProjectNote_Bool_Exp> | null | undefined;
  _not?: ProjectNote_Bool_Exp | null | undefined;
  _or?: Array<ProjectNote_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "rolodex_projectnote" */
export type ProjectNote_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'timestamp';

/** Boolean expression to filter rows from the table "rolodex_projectrole". All fields are combined with a logical 'AND'. */
export type ProjectRole_Bool_Exp = {
  _and?: Array<ProjectRole_Bool_Exp> | null | undefined;
  _not?: ProjectRole_Bool_Exp | null | undefined;
  _or?: Array<ProjectRole_Bool_Exp> | null | undefined;
  assignments?: ProjectAssignment_Bool_Exp | null | undefined;
  assignments_aggregate?: ProjectAssignment_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  position?: Int_Comparison_Exp | null | undefined;
  projectRole?: String_Comparison_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "rolodex_projecttype". All fields are combined with a logical 'AND'. */
export type ProjectType_Bool_Exp = {
  _and?: Array<ProjectType_Bool_Exp> | null | undefined;
  _not?: ProjectType_Bool_Exp | null | undefined;
  _or?: Array<ProjectType_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  projectType?: String_Comparison_Exp | null | undefined;
  projects?: Project_Bool_Exp | null | undefined;
  projects_aggregate?: Project_Aggregate_Bool_Exp | null | undefined;
};

export type Project_Aggregate_Bool_Exp = {
  bool_and?: Project_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Project_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Project_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Project_Aggregate_Bool_Exp_Bool_And = {
  arguments: Project_Select_Column_Project_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Project_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Project_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Project_Select_Column_Project_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Project_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Project_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Project_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Project_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_project". All fields are combined with a logical 'AND'. */
export type Project_Bool_Exp = {
  _and?: Array<Project_Bool_Exp> | null | undefined;
  _not?: Project_Bool_Exp | null | undefined;
  _or?: Array<Project_Bool_Exp> | null | undefined;
  archives?: Archive_Bool_Exp | null | undefined;
  archives_aggregate?: Archive_Aggregate_Bool_Exp | null | undefined;
  assignments?: ProjectAssignment_Bool_Exp | null | undefined;
  assignments_aggregate?: ProjectAssignment_Aggregate_Bool_Exp | null | undefined;
  bloodhound_api_key_id?: String_Comparison_Exp | null | undefined;
  bloodhound_api_key_token?: String_Comparison_Exp | null | undefined;
  bloodhound_api_root_url?: String_Comparison_Exp | null | undefined;
  bloodhound_results?: Jsonb_Comparison_Exp | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  cloudServers?: CloudServer_Bool_Exp | null | undefined;
  cloudServers_aggregate?: CloudServer_Aggregate_Bool_Exp | null | undefined;
  codename?: String_Comparison_Exp | null | undefined;
  collab_note?: String_Comparison_Exp | null | undefined;
  comments?: ProjectNote_Bool_Exp | null | undefined;
  comments_aggregate?: ProjectNote_Aggregate_Bool_Exp | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  contacts?: ProjectContact_Bool_Exp | null | undefined;
  contacts_aggregate?: ProjectContact_Aggregate_Bool_Exp | null | undefined;
  deconflictions?: Deconfliction_Bool_Exp | null | undefined;
  deconflictions_aggregate?: Deconfliction_Aggregate_Bool_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  domainServerConnections?: DomainServerConnection_Bool_Exp | null | undefined;
  domainServerConnections_aggregate?: DomainServerConnection_Aggregate_Bool_Exp | null | undefined;
  domains?: DomainCheckout_Bool_Exp | null | undefined;
  domains_aggregate?: DomainCheckout_Aggregate_Bool_Exp | null | undefined;
  endDate?: Date_Comparison_Exp | null | undefined;
  endTime?: Time_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  invites?: ProjectInvite_Bool_Exp | null | undefined;
  invites_aggregate?: ProjectInvite_Aggregate_Bool_Exp | null | undefined;
  objectives?: Objective_Bool_Exp | null | undefined;
  objectives_aggregate?: Objective_Aggregate_Bool_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  oplogs?: Oplog_Bool_Exp | null | undefined;
  oplogs_aggregate?: Oplog_Aggregate_Bool_Exp | null | undefined;
  projectType?: ProjectType_Bool_Exp | null | undefined;
  projectTypeId?: Bigint_Comparison_Exp | null | undefined;
  reports?: Report_Bool_Exp | null | undefined;
  reports_aggregate?: Report_Aggregate_Bool_Exp | null | undefined;
  scopes?: Scope_Bool_Exp | null | undefined;
  scopes_aggregate?: Scope_Aggregate_Bool_Exp | null | undefined;
  serviceTokenProjectAccesses?: ServiceTokenProjectAccess_Bool_Exp | null | undefined;
  serviceTokenProjectAccesses_aggregate?: ServiceTokenProjectAccess_Aggregate_Bool_Exp | null | undefined;
  slackChannel?: String_Comparison_Exp | null | undefined;
  startDate?: Date_Comparison_Exp | null | undefined;
  startTime?: Time_Comparison_Exp | null | undefined;
  staticServers?: ServerCheckout_Bool_Exp | null | undefined;
  staticServers_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
  targets?: Target_Bool_Exp | null | undefined;
  targets_aggregate?: Target_Aggregate_Bool_Exp | null | undefined;
  timezone?: String_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  whitecards?: Whitecard_Bool_Exp | null | undefined;
  whitecards_aggregate?: Whitecard_Aggregate_Bool_Exp | null | undefined;
};

/** select columns of table "rolodex_project" */
export type Project_Select_Column =
  /** column name */
  | 'bloodhound_api_key_id'
  /** column name */
  | 'bloodhound_api_key_token'
  /** column name */
  | 'bloodhound_api_root_url'
  /** column name */
  | 'bloodhound_results'
  /** column name */
  | 'clientId'
  /** column name */
  | 'codename'
  /** column name */
  | 'collab_note'
  /** column name */
  | 'complete'
  /** column name */
  | 'description'
  /** column name */
  | 'endDate'
  /** column name */
  | 'endTime'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'id'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectTypeId'
  /** column name */
  | 'slackChannel'
  /** column name */
  | 'startDate'
  /** column name */
  | 'startTime'
  /** column name */
  | 'timezone';

/** select "project_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_project" */
export type Project_Select_Column_Project_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'complete';

/** select "project_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_project" */
export type Project_Select_Column_Project_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'complete';

export type ReportConfiguration_Aggregate_Bool_Exp = {
  avg?: ReportConfiguration_Aggregate_Bool_Exp_Avg | null | undefined;
  bool_and?: ReportConfiguration_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ReportConfiguration_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  corr?: ReportConfiguration_Aggregate_Bool_Exp_Corr | null | undefined;
  count?: ReportConfiguration_Aggregate_Bool_Exp_Count | null | undefined;
  covar_samp?: ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp | null | undefined;
  max?: ReportConfiguration_Aggregate_Bool_Exp_Max | null | undefined;
  min?: ReportConfiguration_Aggregate_Bool_Exp_Min | null | undefined;
  stddev_samp?: ReportConfiguration_Aggregate_Bool_Exp_Stddev_Samp | null | undefined;
  sum?: ReportConfiguration_Aggregate_Bool_Exp_Sum | null | undefined;
  var_samp?: ReportConfiguration_Aggregate_Bool_Exp_Var_Samp | null | undefined;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Avg = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Avg_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Bool_And = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Corr = {
  arguments: ReportConfiguration_Aggregate_Bool_Exp_Corr_Arguments;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Corr_Arguments = {
  X: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Corr_Arguments_Columns;
  Y: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Corr_Arguments_Columns;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ReportConfiguration_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp = {
  arguments: ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp_Arguments;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp_Arguments = {
  X: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
  Y: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Max = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Max_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Min = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Min_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Stddev_Samp = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Sum = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Sum_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportConfiguration_Aggregate_Bool_Exp_Var_Samp = {
  arguments: ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportConfiguration_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "commandcenter_reportconfiguration". All fields are combined with a logical 'AND'. */
export type ReportConfiguration_Bool_Exp = {
  _and?: Array<ReportConfiguration_Bool_Exp> | null | undefined;
  _not?: ReportConfiguration_Bool_Exp | null | undefined;
  _or?: Array<ReportConfiguration_Bool_Exp> | null | undefined;
  borderColor?: String_Comparison_Exp | null | undefined;
  borderWeight?: Int_Comparison_Exp | null | undefined;
  default_cvss_version?: String_Comparison_Exp | null | undefined;
  docxTemplate?: Template_Bool_Exp | null | undefined;
  docxTemplateId?: Bigint_Comparison_Exp | null | undefined;
  enableBorders?: Boolean_Comparison_Exp | null | undefined;
  evidence_image_alignment?: String_Comparison_Exp | null | undefined;
  evidence_image_width?: Float8_Comparison_Exp | null | undefined;
  figure_caption_location?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  labelFigure?: String_Comparison_Exp | null | undefined;
  labelTable?: String_Comparison_Exp | null | undefined;
  outline_tags?: String_Comparison_Exp | null | undefined;
  pptxTemplate?: Template_Bool_Exp | null | undefined;
  pptxTemplateId?: Bigint_Comparison_Exp | null | undefined;
  prefixFigure?: String_Comparison_Exp | null | undefined;
  prefixTable?: String_Comparison_Exp | null | undefined;
  project_filename?: String_Comparison_Exp | null | undefined;
  report_filename?: String_Comparison_Exp | null | undefined;
  table_caption_location?: String_Comparison_Exp | null | undefined;
  target_delivery_date?: Int_Comparison_Exp | null | undefined;
  title_case_captions?: Boolean_Comparison_Exp | null | undefined;
  title_case_exceptions?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column =
  /** column name */
  | 'borderColor'
  /** column name */
  | 'borderWeight'
  /** column name */
  | 'default_cvss_version'
  /** column name */
  | 'docxTemplateId'
  /** column name */
  | 'enableBorders'
  /** column name */
  | 'evidence_image_alignment'
  /** column name */
  | 'evidence_image_width'
  /** column name */
  | 'figure_caption_location'
  /** column name */
  | 'id'
  /** column name */
  | 'labelFigure'
  /** column name */
  | 'labelTable'
  /** column name */
  | 'outline_tags'
  /** column name */
  | 'pptxTemplateId'
  /** column name */
  | 'prefixFigure'
  /** column name */
  | 'prefixTable'
  /** column name */
  | 'project_filename'
  /** column name */
  | 'report_filename'
  /** column name */
  | 'table_caption_location'
  /** column name */
  | 'target_delivery_date'
  /** column name */
  | 'title_case_captions'
  /** column name */
  | 'title_case_exceptions';

/** select "reportConfiguration_aggregate_bool_exp_avg_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Avg_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_bool_and_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'enableBorders'
  /** column name */
  | 'title_case_captions';

/** select "reportConfiguration_aggregate_bool_exp_bool_or_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'enableBorders'
  /** column name */
  | 'title_case_captions';

/** select "reportConfiguration_aggregate_bool_exp_corr_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Corr_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_covar_samp_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_max_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Max_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_min_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Min_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_stddev_samp_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_sum_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Sum_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

/** select "reportConfiguration_aggregate_bool_exp_var_samp_arguments_columns" columns of table "commandcenter_reportconfiguration" */
export type ReportConfiguration_Select_Column_ReportConfiguration_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns =
  /** column name */
  | 'evidence_image_width';

export type Report_Aggregate_Bool_Exp = {
  bool_and?: Report_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Report_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Report_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Report_Aggregate_Bool_Exp_Bool_And = {
  arguments: Report_Select_Column_Report_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Report_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Report_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Report_Select_Column_Report_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Report_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Report_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Report_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Report_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_report". All fields are combined with a logical 'AND'. */
export type Report_Bool_Exp = {
  _and?: Array<Report_Bool_Exp> | null | undefined;
  _not?: Report_Bool_Exp | null | undefined;
  _or?: Array<Report_Bool_Exp> | null | undefined;
  archived?: Boolean_Comparison_Exp | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  createdById?: Bigint_Comparison_Exp | null | undefined;
  creation?: Date_Comparison_Exp | null | undefined;
  delivered?: Boolean_Comparison_Exp | null | undefined;
  docxTemplate?: Template_Bool_Exp | null | undefined;
  docxTemplateId?: Bigint_Comparison_Exp | null | undefined;
  evidence?: Evidence_Bool_Exp | null | undefined;
  evidence_aggregate?: Evidence_Aggregate_Bool_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  findings?: ReportedFinding_Bool_Exp | null | undefined;
  findings_aggregate?: ReportedFinding_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  include_bloodhound_data?: Boolean_Comparison_Exp | null | undefined;
  last_update?: Date_Comparison_Exp | null | undefined;
  observations?: ReportedObservation_Bool_Exp | null | undefined;
  observations_aggregate?: ReportedObservation_Aggregate_Bool_Exp | null | undefined;
  pptxTemplate?: Template_Bool_Exp | null | undefined;
  pptxTemplateId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_report" */
export type Report_Select_Column =
  /** column name */
  | 'archived'
  /** column name */
  | 'complete'
  /** column name */
  | 'createdById'
  /** column name */
  | 'creation'
  /** column name */
  | 'delivered'
  /** column name */
  | 'docxTemplateId'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'id'
  /** column name */
  | 'include_bloodhound_data'
  /** column name */
  | 'last_update'
  /** column name */
  | 'pptxTemplateId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'title';

/** select "report_aggregate_bool_exp_bool_and_arguments_columns" columns of table "reporting_report" */
export type Report_Select_Column_Report_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'archived'
  /** column name */
  | 'complete'
  /** column name */
  | 'delivered'
  /** column name */
  | 'include_bloodhound_data';

/** select "report_aggregate_bool_exp_bool_or_arguments_columns" columns of table "reporting_report" */
export type Report_Select_Column_Report_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'archived'
  /** column name */
  | 'complete'
  /** column name */
  | 'delivered'
  /** column name */
  | 'include_bloodhound_data';

export type ReportedFindingNote_Aggregate_Bool_Exp = {
  count?: ReportedFindingNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ReportedFindingNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ReportedFindingNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ReportedFindingNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_localfindingnote". All fields are combined with a logical 'AND'. */
export type ReportedFindingNote_Bool_Exp = {
  _and?: Array<ReportedFindingNote_Bool_Exp> | null | undefined;
  _not?: ReportedFindingNote_Bool_Exp | null | undefined;
  _or?: Array<ReportedFindingNote_Bool_Exp> | null | undefined;
  finding?: ReportedFinding_Bool_Exp | null | undefined;
  findingId?: Bigint_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_localfindingnote" */
export type ReportedFindingNote_Select_Column =
  /** column name */
  | 'findingId'
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'timestamp';

export type ReportedFinding_Aggregate_Bool_Exp = {
  avg?: ReportedFinding_Aggregate_Bool_Exp_Avg | null | undefined;
  bool_and?: ReportedFinding_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ReportedFinding_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  corr?: ReportedFinding_Aggregate_Bool_Exp_Corr | null | undefined;
  count?: ReportedFinding_Aggregate_Bool_Exp_Count | null | undefined;
  covar_samp?: ReportedFinding_Aggregate_Bool_Exp_Covar_Samp | null | undefined;
  max?: ReportedFinding_Aggregate_Bool_Exp_Max | null | undefined;
  min?: ReportedFinding_Aggregate_Bool_Exp_Min | null | undefined;
  stddev_samp?: ReportedFinding_Aggregate_Bool_Exp_Stddev_Samp | null | undefined;
  sum?: ReportedFinding_Aggregate_Bool_Exp_Sum | null | undefined;
  var_samp?: ReportedFinding_Aggregate_Bool_Exp_Var_Samp | null | undefined;
};

export type ReportedFinding_Aggregate_Bool_Exp_Avg = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Avg_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Bool_And = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Corr = {
  arguments: ReportedFinding_Aggregate_Bool_Exp_Corr_Arguments;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Corr_Arguments = {
  X: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Corr_Arguments_Columns;
  Y: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Corr_Arguments_Columns;
};

export type ReportedFinding_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ReportedFinding_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Covar_Samp = {
  arguments: ReportedFinding_Aggregate_Bool_Exp_Covar_Samp_Arguments;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Covar_Samp_Arguments = {
  X: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
  Y: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
};

export type ReportedFinding_Aggregate_Bool_Exp_Max = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Max_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Min = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Min_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Stddev_Samp = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Sum = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Sum_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type ReportedFinding_Aggregate_Bool_Exp_Var_Samp = {
  arguments: ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedFinding_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_reportfindinglink". All fields are combined with a logical 'AND'. */
export type ReportedFinding_Bool_Exp = {
  _and?: Array<ReportedFinding_Bool_Exp> | null | undefined;
  _not?: ReportedFinding_Bool_Exp | null | undefined;
  _or?: Array<ReportedFinding_Bool_Exp> | null | undefined;
  addedAsBlank?: Boolean_Comparison_Exp | null | undefined;
  affectedEntities?: String_Comparison_Exp | null | undefined;
  assignedTo?: User_Bool_Exp | null | undefined;
  assignedToId?: Bigint_Comparison_Exp | null | undefined;
  comments?: ReportedFindingNote_Bool_Exp | null | undefined;
  comments_aggregate?: ReportedFindingNote_Aggregate_Bool_Exp | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  cvssScore?: Float8_Comparison_Exp | null | undefined;
  cvssVector?: String_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  findingGuidance?: String_Comparison_Exp | null | undefined;
  findingType?: FindingType_Bool_Exp | null | undefined;
  findingTypeId?: Bigint_Comparison_Exp | null | undefined;
  hostDetectionTechniques?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  impact?: String_Comparison_Exp | null | undefined;
  mitigation?: String_Comparison_Exp | null | undefined;
  networkDetectionTechniques?: String_Comparison_Exp | null | undefined;
  position?: Int_Comparison_Exp | null | undefined;
  references?: String_Comparison_Exp | null | undefined;
  replication_steps?: String_Comparison_Exp | null | undefined;
  report?: Report_Bool_Exp | null | undefined;
  reportId?: Bigint_Comparison_Exp | null | undefined;
  severity?: FindingSeverity_Bool_Exp | null | undefined;
  severityId?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column =
  /** column name */
  | 'addedAsBlank'
  /** column name */
  | 'affectedEntities'
  /** column name */
  | 'assignedToId'
  /** column name */
  | 'complete'
  /** column name */
  | 'cvssScore'
  /** column name */
  | 'cvssVector'
  /** column name */
  | 'description'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'findingGuidance'
  /** column name */
  | 'findingTypeId'
  /** column name */
  | 'hostDetectionTechniques'
  /** column name */
  | 'id'
  /** column name */
  | 'impact'
  /** column name */
  | 'mitigation'
  /** column name */
  | 'networkDetectionTechniques'
  /** column name */
  | 'position'
  /** column name */
  | 'references'
  /** column name */
  | 'replication_steps'
  /** column name */
  | 'reportId'
  /** column name */
  | 'severityId'
  /** column name */
  | 'title';

/** select "reportedFinding_aggregate_bool_exp_avg_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Avg_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_bool_and_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'addedAsBlank'
  /** column name */
  | 'complete';

/** select "reportedFinding_aggregate_bool_exp_bool_or_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'addedAsBlank'
  /** column name */
  | 'complete';

/** select "reportedFinding_aggregate_bool_exp_corr_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Corr_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_covar_samp_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_max_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Max_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_min_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Min_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_stddev_samp_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_sum_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Sum_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** select "reportedFinding_aggregate_bool_exp_var_samp_arguments_columns" columns of table "reporting_reportfindinglink" */
export type ReportedFinding_Select_Column_ReportedFinding_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns =
  /** column name */
  | 'cvssScore';

/** input type for updating data in table "reporting_reportfindinglink" */
export type ReportedFinding_Set_Input = {
  addedAsBlank?: boolean | null | undefined;
  affectedEntities?: string | null | undefined;
  assignedToId?: number | null | undefined;
  complete?: boolean | null | undefined;
  cvssScore?: number | null | undefined;
  cvssVector?: string | null | undefined;
  description?: string | null | undefined;
  extraFields?: Record<string, unknown> | null | undefined;
  findingGuidance?: string | null | undefined;
  findingTypeId?: number | null | undefined;
  hostDetectionTechniques?: string | null | undefined;
  id?: number | null | undefined;
  impact?: string | null | undefined;
  mitigation?: string | null | undefined;
  networkDetectionTechniques?: string | null | undefined;
  position?: number | null | undefined;
  references?: string | null | undefined;
  replication_steps?: string | null | undefined;
  reportId?: number | null | undefined;
  severityId?: number | null | undefined;
  title?: string | null | undefined;
};

export type ReportedObservation_Aggregate_Bool_Exp = {
  bool_and?: ReportedObservation_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: ReportedObservation_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: ReportedObservation_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ReportedObservation_Aggregate_Bool_Exp_Bool_And = {
  arguments: ReportedObservation_Select_Column_ReportedObservation_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedObservation_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportedObservation_Aggregate_Bool_Exp_Bool_Or = {
  arguments: ReportedObservation_Select_Column_ReportedObservation_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: ReportedObservation_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type ReportedObservation_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ReportedObservation_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ReportedObservation_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_reportobservationlink". All fields are combined with a logical 'AND'. */
export type ReportedObservation_Bool_Exp = {
  _and?: Array<ReportedObservation_Bool_Exp> | null | undefined;
  _not?: ReportedObservation_Bool_Exp | null | undefined;
  _or?: Array<ReportedObservation_Bool_Exp> | null | undefined;
  added_as_blank?: Boolean_Comparison_Exp | null | undefined;
  assigned_to_id?: Bigint_Comparison_Exp | null | undefined;
  asssignedTo?: User_Bool_Exp | null | undefined;
  complete?: Boolean_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  position?: Int_Comparison_Exp | null | undefined;
  report?: Report_Bool_Exp | null | undefined;
  report_id?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "reporting_reportobservationlink" */
export type ReportedObservation_Select_Column =
  /** column name */
  | 'added_as_blank'
  /** column name */
  | 'assigned_to_id'
  /** column name */
  | 'complete'
  /** column name */
  | 'description'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'id'
  /** column name */
  | 'position'
  /** column name */
  | 'report_id'
  /** column name */
  | 'title';

/** select "reportedObservation_aggregate_bool_exp_bool_and_arguments_columns" columns of table "reporting_reportobservationlink" */
export type ReportedObservation_Select_Column_ReportedObservation_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'added_as_blank'
  /** column name */
  | 'complete';

/** select "reportedObservation_aggregate_bool_exp_bool_or_arguments_columns" columns of table "reporting_reportobservationlink" */
export type ReportedObservation_Select_Column_ReportedObservation_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'added_as_blank'
  /** column name */
  | 'complete';

export type Scope_Aggregate_Bool_Exp = {
  bool_and?: Scope_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Scope_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Scope_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Scope_Aggregate_Bool_Exp_Bool_And = {
  arguments: Scope_Select_Column_Scope_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Scope_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Scope_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Scope_Select_Column_Scope_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Scope_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Scope_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Scope_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Scope_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projectscope". All fields are combined with a logical 'AND'. */
export type Scope_Bool_Exp = {
  _and?: Array<Scope_Bool_Exp> | null | undefined;
  _not?: Scope_Bool_Exp | null | undefined;
  _or?: Array<Scope_Bool_Exp> | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  disallowed?: Boolean_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  requiresCaution?: Boolean_Comparison_Exp | null | undefined;
  scope?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projectscope" */
export type Scope_Select_Column =
  /** column name */
  | 'description'
  /** column name */
  | 'disallowed'
  /** column name */
  | 'id'
  /** column name */
  | 'name'
  /** column name */
  | 'projectId'
  /** column name */
  | 'requiresCaution'
  /** column name */
  | 'scope';

/** select "scope_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_projectscope" */
export type Scope_Select_Column_Scope_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'disallowed'
  /** column name */
  | 'requiresCaution';

/** select "scope_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_projectscope" */
export type Scope_Select_Column_Scope_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'disallowed'
  /** column name */
  | 'requiresCaution';

export type ServerCheckout_Aggregate_Bool_Exp = {
  count?: ServerCheckout_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServerCheckout_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServerCheckout_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServerCheckout_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_serverhistory". All fields are combined with a logical 'AND'. */
export type ServerCheckout_Bool_Exp = {
  _and?: Array<ServerCheckout_Bool_Exp> | null | undefined;
  _not?: ServerCheckout_Bool_Exp | null | undefined;
  _or?: Array<ServerCheckout_Bool_Exp> | null | undefined;
  activityType?: ActivityType_Bool_Exp | null | undefined;
  activityTypeId?: Bigint_Comparison_Exp | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  domainServerConnections?: DomainServerConnection_Bool_Exp | null | undefined;
  domainServerConnections_aggregate?: DomainServerConnection_Aggregate_Bool_Exp | null | undefined;
  endDate?: Date_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  server?: StaticServer_Bool_Exp | null | undefined;
  serverId?: Bigint_Comparison_Exp | null | undefined;
  serverRole?: ServerRole_Bool_Exp | null | undefined;
  serverRoleId?: Bigint_Comparison_Exp | null | undefined;
  startDate?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_serverhistory" */
export type ServerCheckout_Select_Column =
  /** column name */
  | 'activityTypeId'
  /** column name */
  | 'clientId'
  /** column name */
  | 'description'
  /** column name */
  | 'endDate'
  /** column name */
  | 'id'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'projectId'
  /** column name */
  | 'serverId'
  /** column name */
  | 'serverRoleId'
  /** column name */
  | 'startDate';

export type ServerNote_Aggregate_Bool_Exp = {
  count?: ServerNote_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServerNote_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServerNote_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServerNote_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_servernote". All fields are combined with a logical 'AND'. */
export type ServerNote_Bool_Exp = {
  _and?: Array<ServerNote_Bool_Exp> | null | undefined;
  _not?: ServerNote_Bool_Exp | null | undefined;
  _or?: Array<ServerNote_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  note?: String_Comparison_Exp | null | undefined;
  operatorId?: Bigint_Comparison_Exp | null | undefined;
  serverId?: Bigint_Comparison_Exp | null | undefined;
  staticServer?: StaticServer_Bool_Exp | null | undefined;
  timestamp?: Date_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_servernote" */
export type ServerNote_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'note'
  /** column name */
  | 'operatorId'
  /** column name */
  | 'serverId'
  /** column name */
  | 'timestamp';

/** Boolean expression to filter rows from the table "shepherd_serverprovider". All fields are combined with a logical 'AND'. */
export type ServerProvider_Bool_Exp = {
  _and?: Array<ServerProvider_Bool_Exp> | null | undefined;
  _not?: ServerProvider_Bool_Exp | null | undefined;
  _or?: Array<ServerProvider_Bool_Exp> | null | undefined;
  cloudServers?: CloudServer_Bool_Exp | null | undefined;
  cloudServers_aggregate?: CloudServer_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  serverProvider?: String_Comparison_Exp | null | undefined;
  staticServers?: StaticServer_Bool_Exp | null | undefined;
  staticServers_aggregate?: StaticServer_Aggregate_Bool_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "shepherd_serverrole". All fields are combined with a logical 'AND'. */
export type ServerRole_Bool_Exp = {
  _and?: Array<ServerRole_Bool_Exp> | null | undefined;
  _not?: ServerRole_Bool_Exp | null | undefined;
  _or?: Array<ServerRole_Bool_Exp> | null | undefined;
  cloudServers?: CloudServer_Bool_Exp | null | undefined;
  cloudServers_aggregate?: CloudServer_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  serverRole?: String_Comparison_Exp | null | undefined;
  staticServers?: ServerCheckout_Bool_Exp | null | undefined;
  staticServers_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "shepherd_serverstatus". All fields are combined with a logical 'AND'. */
export type ServerStatus_Bool_Exp = {
  _and?: Array<ServerStatus_Bool_Exp> | null | undefined;
  _not?: ServerStatus_Bool_Exp | null | undefined;
  _or?: Array<ServerStatus_Bool_Exp> | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  serverStatus?: String_Comparison_Exp | null | undefined;
  servers?: StaticServer_Bool_Exp | null | undefined;
  servers_aggregate?: StaticServer_Aggregate_Bool_Exp | null | undefined;
};

export type ServiceTokenDomainAccess_Aggregate_Bool_Exp = {
  count?: ServiceTokenDomainAccess_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServiceTokenDomainAccess_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServiceTokenDomainAccess_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServiceTokenDomainAccess_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "api_service_token_domain_access". All fields are combined with a logical 'AND'. */
export type ServiceTokenDomainAccess_Bool_Exp = {
  _and?: Array<ServiceTokenDomainAccess_Bool_Exp> | null | undefined;
  _not?: ServiceTokenDomainAccess_Bool_Exp | null | undefined;
  _or?: Array<ServiceTokenDomainAccess_Bool_Exp> | null | undefined;
  domain?: Domain_Bool_Exp | null | undefined;
  domainId?: Bigint_Comparison_Exp | null | undefined;
  tokenId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "api_service_token_domain_access" */
export type ServiceTokenDomainAccess_Select_Column =
  /** column name */
  | 'domainId'
  /** column name */
  | 'tokenId';

export type ServiceTokenProjectAccess_Aggregate_Bool_Exp = {
  count?: ServiceTokenProjectAccess_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServiceTokenProjectAccess_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServiceTokenProjectAccess_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServiceTokenProjectAccess_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "api_service_token_project_access". All fields are combined with a logical 'AND'. */
export type ServiceTokenProjectAccess_Bool_Exp = {
  _and?: Array<ServiceTokenProjectAccess_Bool_Exp> | null | undefined;
  _not?: ServiceTokenProjectAccess_Bool_Exp | null | undefined;
  _or?: Array<ServiceTokenProjectAccess_Bool_Exp> | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  tokenId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "api_service_token_project_access" */
export type ServiceTokenProjectAccess_Select_Column =
  /** column name */
  | 'projectId'
  /** column name */
  | 'tokenId';

export type ServiceTokenStaticServerAccess_Aggregate_Bool_Exp = {
  count?: ServiceTokenStaticServerAccess_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServiceTokenStaticServerAccess_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServiceTokenStaticServerAccess_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServiceTokenStaticServerAccess_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "api_service_token_static_server_access". All fields are combined with a logical 'AND'. */
export type ServiceTokenStaticServerAccess_Bool_Exp = {
  _and?: Array<ServiceTokenStaticServerAccess_Bool_Exp> | null | undefined;
  _not?: ServiceTokenStaticServerAccess_Bool_Exp | null | undefined;
  _or?: Array<ServiceTokenStaticServerAccess_Bool_Exp> | null | undefined;
  serverId?: Bigint_Comparison_Exp | null | undefined;
  staticServer?: StaticServer_Bool_Exp | null | undefined;
  tokenId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "api_service_token_static_server_access" */
export type ServiceTokenStaticServerAccess_Select_Column =
  /** column name */
  | 'serverId'
  /** column name */
  | 'tokenId';

export type ServiceTokenUserAccess_Aggregate_Bool_Exp = {
  count?: ServiceTokenUserAccess_Aggregate_Bool_Exp_Count | null | undefined;
};

export type ServiceTokenUserAccess_Aggregate_Bool_Exp_Count = {
  arguments?: Array<ServiceTokenUserAccess_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: ServiceTokenUserAccess_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "api_service_token_user_access". All fields are combined with a logical 'AND'. */
export type ServiceTokenUserAccess_Bool_Exp = {
  _and?: Array<ServiceTokenUserAccess_Bool_Exp> | null | undefined;
  _not?: ServiceTokenUserAccess_Bool_Exp | null | undefined;
  _or?: Array<ServiceTokenUserAccess_Bool_Exp> | null | undefined;
  tokenId?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  userId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "api_service_token_user_access" */
export type ServiceTokenUserAccess_Select_Column =
  /** column name */
  | 'tokenId'
  /** column name */
  | 'userId';

/** Boolean expression to compare columns of type "smallint". All fields are combined with logical 'AND'. */
export type Smallint_Comparison_Exp = {
  _eq?: number | null | undefined;
  _gt?: number | null | undefined;
  _gte?: number | null | undefined;
  _in?: Array<number> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: number | null | undefined;
  _lte?: number | null | undefined;
  _neq?: number | null | undefined;
  _nin?: Array<number> | null | undefined;
};

export type StaticServer_Aggregate_Bool_Exp = {
  count?: StaticServer_Aggregate_Bool_Exp_Count | null | undefined;
};

export type StaticServer_Aggregate_Bool_Exp_Count = {
  arguments?: Array<StaticServer_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: StaticServer_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "shepherd_staticserver". All fields are combined with a logical 'AND'. */
export type StaticServer_Bool_Exp = {
  _and?: Array<StaticServer_Bool_Exp> | null | undefined;
  _not?: StaticServer_Bool_Exp | null | undefined;
  _or?: Array<StaticServer_Bool_Exp> | null | undefined;
  auxServerAddresses?: AuxServerAddresses_Bool_Exp | null | undefined;
  auxServerAddresses_aggregate?: AuxServerAddresses_Aggregate_Bool_Exp | null | undefined;
  checkouts?: ServerCheckout_Bool_Exp | null | undefined;
  checkouts_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
  comments?: ServerNote_Bool_Exp | null | undefined;
  comments_aggregate?: ServerNote_Aggregate_Bool_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  extraFields?: Jsonb_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  ipAddress?: Inet_Comparison_Exp | null | undefined;
  lastUsedById?: Bigint_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  serverProvider?: ServerProvider_Bool_Exp | null | undefined;
  serverProviderId?: Bigint_Comparison_Exp | null | undefined;
  serverStatus?: ServerStatus_Bool_Exp | null | undefined;
  serverStatusId?: Bigint_Comparison_Exp | null | undefined;
  serviceTokenStaticServerAccesses?: ServiceTokenStaticServerAccess_Bool_Exp | null | undefined;
  serviceTokenStaticServerAccesses_aggregate?: ServiceTokenStaticServerAccess_Aggregate_Bool_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "shepherd_staticserver" */
export type StaticServer_Select_Column =
  /** column name */
  | 'description'
  /** column name */
  | 'extraFields'
  /** column name */
  | 'id'
  /** column name */
  | 'ipAddress'
  /** column name */
  | 'lastUsedById'
  /** column name */
  | 'name'
  /** column name */
  | 'serverProviderId'
  /** column name */
  | 'serverStatusId';

/** Boolean expression to filter rows from the table "taggit_tag". All fields are combined with a logical 'AND'. */
export type Tag_Bool_Exp = {
  _and?: Array<Tag_Bool_Exp> | null | undefined;
  _not?: Tag_Bool_Exp | null | undefined;
  _or?: Array<Tag_Bool_Exp> | null | undefined;
  id?: Int_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  slug?: String_Comparison_Exp | null | undefined;
  taggedItem?: TaggedItem_Bool_Exp | null | undefined;
  taggedItem_aggregate?: TaggedItem_Aggregate_Bool_Exp | null | undefined;
};

export type TaggedItem_Aggregate_Bool_Exp = {
  count?: TaggedItem_Aggregate_Bool_Exp_Count | null | undefined;
};

export type TaggedItem_Aggregate_Bool_Exp_Count = {
  arguments?: Array<TaggedItem_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: TaggedItem_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "taggit_taggeditem". All fields are combined with a logical 'AND'. */
export type TaggedItem_Bool_Exp = {
  _and?: Array<TaggedItem_Bool_Exp> | null | undefined;
  _not?: TaggedItem_Bool_Exp | null | undefined;
  _or?: Array<TaggedItem_Bool_Exp> | null | undefined;
  contentType?: DjangoContentType_Bool_Exp | null | undefined;
  content_type_id?: Int_Comparison_Exp | null | undefined;
  id?: Int_Comparison_Exp | null | undefined;
  object_id?: Int_Comparison_Exp | null | undefined;
  tag?: Tag_Bool_Exp | null | undefined;
  tag_id?: Int_Comparison_Exp | null | undefined;
  taggedItem?: DjangoContentType_Bool_Exp | null | undefined;
};

/** select columns of table "taggit_taggeditem" */
export type TaggedItem_Select_Column =
  /** column name */
  | 'content_type_id'
  /** column name */
  | 'id'
  /** column name */
  | 'object_id'
  /** column name */
  | 'tag_id';

export type Target_Aggregate_Bool_Exp = {
  bool_and?: Target_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Target_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  count?: Target_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Target_Aggregate_Bool_Exp_Bool_And = {
  arguments: Target_Select_Column_Target_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Target_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Target_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Target_Select_Column_Target_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Target_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Target_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Target_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Target_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_projecttarget". All fields are combined with a logical 'AND'. */
export type Target_Bool_Exp = {
  _and?: Array<Target_Bool_Exp> | null | undefined;
  _not?: Target_Bool_Exp | null | undefined;
  _or?: Array<Target_Bool_Exp> | null | undefined;
  compromised?: Boolean_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  hostname?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  ipAddress?: String_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_projecttarget" */
export type Target_Select_Column =
  /** column name */
  | 'compromised'
  /** column name */
  | 'description'
  /** column name */
  | 'hostname'
  /** column name */
  | 'id'
  /** column name */
  | 'ipAddress'
  /** column name */
  | 'projectId';

/** select "target_aggregate_bool_exp_bool_and_arguments_columns" columns of table "rolodex_projecttarget" */
export type Target_Select_Column_Target_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'compromised';

/** select "target_aggregate_bool_exp_bool_or_arguments_columns" columns of table "rolodex_projecttarget" */
export type Target_Select_Column_Target_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'compromised';

export type Template_Aggregate_Bool_Exp = {
  avg?: Template_Aggregate_Bool_Exp_Avg | null | undefined;
  bool_and?: Template_Aggregate_Bool_Exp_Bool_And | null | undefined;
  bool_or?: Template_Aggregate_Bool_Exp_Bool_Or | null | undefined;
  corr?: Template_Aggregate_Bool_Exp_Corr | null | undefined;
  count?: Template_Aggregate_Bool_Exp_Count | null | undefined;
  covar_samp?: Template_Aggregate_Bool_Exp_Covar_Samp | null | undefined;
  max?: Template_Aggregate_Bool_Exp_Max | null | undefined;
  min?: Template_Aggregate_Bool_Exp_Min | null | undefined;
  stddev_samp?: Template_Aggregate_Bool_Exp_Stddev_Samp | null | undefined;
  sum?: Template_Aggregate_Bool_Exp_Sum | null | undefined;
  var_samp?: Template_Aggregate_Bool_Exp_Var_Samp | null | undefined;
};

export type Template_Aggregate_Bool_Exp_Avg = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Avg_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Bool_And = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Bool_And_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Bool_Or = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Boolean_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Corr = {
  arguments: Template_Aggregate_Bool_Exp_Corr_Arguments;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Corr_Arguments = {
  X: Template_Select_Column_Template_Aggregate_Bool_Exp_Corr_Arguments_Columns;
  Y: Template_Select_Column_Template_Aggregate_Bool_Exp_Corr_Arguments_Columns;
};

export type Template_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Template_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Covar_Samp = {
  arguments: Template_Aggregate_Bool_Exp_Covar_Samp_Arguments;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Covar_Samp_Arguments = {
  X: Template_Select_Column_Template_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
  Y: Template_Select_Column_Template_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns;
};

export type Template_Aggregate_Bool_Exp_Max = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Max_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Min = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Min_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Stddev_Samp = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Sum = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Sum_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

export type Template_Aggregate_Bool_Exp_Var_Samp = {
  arguments: Template_Select_Column_Template_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns;
  distinct?: boolean | null | undefined;
  filter?: Template_Bool_Exp | null | undefined;
  predicate: Float8_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "reporting_reporttemplate". All fields are combined with a logical 'AND'. */
export type Template_Bool_Exp = {
  _and?: Array<Template_Bool_Exp> | null | undefined;
  _not?: Template_Bool_Exp | null | undefined;
  _or?: Array<Template_Bool_Exp> | null | undefined;
  bloodhoundHeadingOffset?: Smallint_Comparison_Exp | null | undefined;
  changelog?: String_Comparison_Exp | null | undefined;
  client?: Client_Bool_Exp | null | undefined;
  clientId?: Bigint_Comparison_Exp | null | undefined;
  commandcenterReportconfigurationsByDefaultPptxTemplateId?: ReportConfiguration_Bool_Exp | null | undefined;
  commandcenterReportconfigurationsByDefaultPptxTemplateId_aggregate?: ReportConfiguration_Aggregate_Bool_Exp | null | undefined;
  commandcenter_reportconfigurations?: ReportConfiguration_Bool_Exp | null | undefined;
  commandcenter_reportconfigurations_aggregate?: ReportConfiguration_Aggregate_Bool_Exp | null | undefined;
  containsBloodhoundData?: Boolean_Comparison_Exp | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  docTypeId?: Bigint_Comparison_Exp | null | undefined;
  document?: String_Comparison_Exp | null | undefined;
  docxTemplates?: Report_Bool_Exp | null | undefined;
  docxTemplates_aggregate?: Report_Aggregate_Bool_Exp | null | undefined;
  evidenceImageAlignment?: String_Comparison_Exp | null | undefined;
  evidenceImageWidth?: Float8_Comparison_Exp | null | undefined;
  filename_override?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  landscape?: Boolean_Comparison_Exp | null | undefined;
  lastUpdate?: Date_Comparison_Exp | null | undefined;
  lintResult?: Jsonb_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  pStyle?: String_Comparison_Exp | null | undefined;
  pptxTemplates?: Report_Bool_Exp | null | undefined;
  pptxTemplates_aggregate?: Report_Aggregate_Bool_Exp | null | undefined;
  protected?: Boolean_Comparison_Exp | null | undefined;
  reporting_doctype?: DocType_Bool_Exp | null | undefined;
  uploadDate?: Date_Comparison_Exp | null | undefined;
  uploadedById?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
};

/** select columns of table "reporting_reporttemplate" */
export type Template_Select_Column =
  /** column name */
  | 'bloodhoundHeadingOffset'
  /** column name */
  | 'changelog'
  /** column name */
  | 'clientId'
  /** column name */
  | 'containsBloodhoundData'
  /** column name */
  | 'description'
  /** column name */
  | 'docTypeId'
  /** column name */
  | 'document'
  /** column name */
  | 'evidenceImageAlignment'
  /** column name */
  | 'evidenceImageWidth'
  /** column name */
  | 'filename_override'
  /** column name */
  | 'id'
  /** column name */
  | 'landscape'
  /** column name */
  | 'lastUpdate'
  /** column name */
  | 'lintResult'
  /** column name */
  | 'name'
  /** column name */
  | 'pStyle'
  /** column name */
  | 'protected'
  /** column name */
  | 'uploadDate'
  /** column name */
  | 'uploadedById';

/** select "template_aggregate_bool_exp_avg_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Avg_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_bool_and_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Bool_And_Arguments_Columns =
  /** column name */
  | 'containsBloodhoundData'
  /** column name */
  | 'landscape'
  /** column name */
  | 'protected';

/** select "template_aggregate_bool_exp_bool_or_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Bool_Or_Arguments_Columns =
  /** column name */
  | 'containsBloodhoundData'
  /** column name */
  | 'landscape'
  /** column name */
  | 'protected';

/** select "template_aggregate_bool_exp_corr_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Corr_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_covar_samp_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Covar_Samp_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_max_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Max_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_min_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Min_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_stddev_samp_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Stddev_Samp_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_sum_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Sum_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** select "template_aggregate_bool_exp_var_samp_arguments_columns" columns of table "reporting_reporttemplate" */
export type Template_Select_Column_Template_Aggregate_Bool_Exp_Var_Samp_Arguments_Columns =
  /** column name */
  | 'evidenceImageWidth';

/** Boolean expression to compare columns of type "time". All fields are combined with logical 'AND'. */
export type Time_Comparison_Exp = {
  _eq?: string | null | undefined;
  _gt?: string | null | undefined;
  _gte?: string | null | undefined;
  _in?: Array<string> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: string | null | undefined;
  _lte?: string | null | undefined;
  _neq?: string | null | undefined;
  _nin?: Array<string> | null | undefined;
};

/** Boolean expression to compare columns of type "timestamptz". All fields are combined with logical 'AND'. */
export type Timestamptz_Comparison_Exp = {
  _eq?: string | null | undefined;
  _gt?: string | null | undefined;
  _gte?: string | null | undefined;
  _in?: Array<string> | null | undefined;
  _is_null?: boolean | null | undefined;
  _lt?: string | null | undefined;
  _lte?: string | null | undefined;
  _neq?: string | null | undefined;
  _nin?: Array<string> | null | undefined;
};

export type UserGroup_Aggregate_Bool_Exp = {
  count?: UserGroup_Aggregate_Bool_Exp_Count | null | undefined;
};

export type UserGroup_Aggregate_Bool_Exp_Count = {
  arguments?: Array<UserGroup_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: UserGroup_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "users_user_groups". All fields are combined with a logical 'AND'. */
export type UserGroup_Bool_Exp = {
  _and?: Array<UserGroup_Bool_Exp> | null | undefined;
  _not?: UserGroup_Bool_Exp | null | undefined;
  _or?: Array<UserGroup_Bool_Exp> | null | undefined;
  authGroup?: Group_Bool_Exp | null | undefined;
  groupId?: Int_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  userId?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "users_user_groups" */
export type UserGroup_Select_Column =
  /** column name */
  | 'groupId'
  /** column name */
  | 'id'
  /** column name */
  | 'userId';

export type UserPermission_Aggregate_Bool_Exp = {
  count?: UserPermission_Aggregate_Bool_Exp_Count | null | undefined;
};

export type UserPermission_Aggregate_Bool_Exp_Count = {
  arguments?: Array<UserPermission_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: UserPermission_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "users_user_user_permissions". All fields are combined with a logical 'AND'. */
export type UserPermission_Bool_Exp = {
  _and?: Array<UserPermission_Bool_Exp> | null | undefined;
  _not?: UserPermission_Bool_Exp | null | undefined;
  _or?: Array<UserPermission_Bool_Exp> | null | undefined;
  authPermission?: AuthPermission_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  permissionId?: Int_Comparison_Exp | null | undefined;
  user_id?: Bigint_Comparison_Exp | null | undefined;
};

/** select columns of table "users_user_user_permissions" */
export type UserPermission_Select_Column =
  /** column name */
  | 'id'
  /** column name */
  | 'permissionId'
  /** column name */
  | 'user_id';

/** Boolean expression to filter rows from the table "home_userprofile". All fields are combined with a logical 'AND'. */
export type UserProfile_Bool_Exp = {
  _and?: Array<UserProfile_Bool_Exp> | null | undefined;
  _not?: UserProfile_Bool_Exp | null | undefined;
  _or?: Array<UserProfile_Bool_Exp> | null | undefined;
  avatar?: String_Comparison_Exp | null | undefined;
  hide_quickstart?: Boolean_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  user?: User_Bool_Exp | null | undefined;
  userId?: Bigint_Comparison_Exp | null | undefined;
};

/** Boolean expression to filter rows from the table "users_user". All fields are combined with a logical 'AND'. */
export type User_Bool_Exp = {
  _and?: Array<User_Bool_Exp> | null | undefined;
  _not?: User_Bool_Exp | null | undefined;
  _or?: Array<User_Bool_Exp> | null | undefined;
  assignments?: ProjectAssignment_Bool_Exp | null | undefined;
  assignments_aggregate?: ProjectAssignment_Aggregate_Bool_Exp | null | undefined;
  clientInvites?: ClientInvite_Bool_Exp | null | undefined;
  clientInvites_aggregate?: ClientInvite_Aggregate_Bool_Exp | null | undefined;
  clientNotes?: ClientNote_Bool_Exp | null | undefined;
  clientNotes_aggregate?: ClientNote_Aggregate_Bool_Exp | null | undefined;
  cloudServers?: CloudServer_Bool_Exp | null | undefined;
  cloudServers_aggregate?: CloudServer_Aggregate_Bool_Exp | null | undefined;
  dateJoined?: Timestamptz_Comparison_Exp | null | undefined;
  domainCheckouts?: DomainCheckout_Bool_Exp | null | undefined;
  domainCheckouts_aggregate?: DomainCheckout_Aggregate_Bool_Exp | null | undefined;
  domainNotes?: DomainNote_Bool_Exp | null | undefined;
  domainNotes_aggregate?: DomainNote_Aggregate_Bool_Exp | null | undefined;
  domains?: Domain_Bool_Exp | null | undefined;
  domains_aggregate?: Domain_Aggregate_Bool_Exp | null | undefined;
  email?: String_Comparison_Exp | null | undefined;
  enable_finding_create?: Boolean_Comparison_Exp | null | undefined;
  enable_finding_delete?: Boolean_Comparison_Exp | null | undefined;
  enable_finding_edit?: Boolean_Comparison_Exp | null | undefined;
  enable_observation_create?: Boolean_Comparison_Exp | null | undefined;
  enable_observation_delete?: Boolean_Comparison_Exp | null | undefined;
  enable_observation_edit?: Boolean_Comparison_Exp | null | undefined;
  enable_template_management?: Boolean_Comparison_Exp | null | undefined;
  evidences?: Evidence_Bool_Exp | null | undefined;
  evidences_aggregate?: Evidence_Aggregate_Bool_Exp | null | undefined;
  findingNotes?: FindingNote_Bool_Exp | null | undefined;
  findingNotes_aggregate?: FindingNote_Aggregate_Bool_Exp | null | undefined;
  groups?: UserGroup_Bool_Exp | null | undefined;
  groups_aggregate?: UserGroup_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  isActive?: Boolean_Comparison_Exp | null | undefined;
  isStaff?: Boolean_Comparison_Exp | null | undefined;
  isSuperuser?: Boolean_Comparison_Exp | null | undefined;
  lastLogin?: Timestamptz_Comparison_Exp | null | undefined;
  name?: String_Comparison_Exp | null | undefined;
  password?: String_Comparison_Exp | null | undefined;
  phone?: String_Comparison_Exp | null | undefined;
  profile?: UserProfile_Bool_Exp | null | undefined;
  projectInvites?: ProjectInvite_Bool_Exp | null | undefined;
  projectInvites_aggregate?: ProjectInvite_Aggregate_Bool_Exp | null | undefined;
  projectNotes?: ProjectNote_Bool_Exp | null | undefined;
  projectNotes_aggregate?: ProjectNote_Aggregate_Bool_Exp | null | undefined;
  projects?: Project_Bool_Exp | null | undefined;
  projects_aggregate?: Project_Aggregate_Bool_Exp | null | undefined;
  reportTemplates?: Template_Bool_Exp | null | undefined;
  reportTemplates_aggregate?: Template_Aggregate_Bool_Exp | null | undefined;
  report_email?: String_Comparison_Exp | null | undefined;
  reportedFindingNotes?: ReportedFindingNote_Bool_Exp | null | undefined;
  reportedFindingNotes_aggregate?: ReportedFindingNote_Aggregate_Bool_Exp | null | undefined;
  reportedFindings?: ReportedFinding_Bool_Exp | null | undefined;
  reportedFindings_aggregate?: ReportedFinding_Aggregate_Bool_Exp | null | undefined;
  reportedObservations?: ReportedObservation_Bool_Exp | null | undefined;
  reportedObservations_aggregate?: ReportedObservation_Aggregate_Bool_Exp | null | undefined;
  reports?: Report_Bool_Exp | null | undefined;
  reports_aggregate?: Report_Aggregate_Bool_Exp | null | undefined;
  require_2fa?: Boolean_Comparison_Exp | null | undefined;
  role?: String_Comparison_Exp | null | undefined;
  serverCheckouts?: ServerCheckout_Bool_Exp | null | undefined;
  serverCheckouts_aggregate?: ServerCheckout_Aggregate_Bool_Exp | null | undefined;
  serverNotes?: ServerNote_Bool_Exp | null | undefined;
  serverNotes_aggregate?: ServerNote_Aggregate_Bool_Exp | null | undefined;
  servers?: StaticServer_Bool_Exp | null | undefined;
  servers_aggregate?: StaticServer_Aggregate_Bool_Exp | null | undefined;
  serviceTokenUserAccesses?: ServiceTokenUserAccess_Bool_Exp | null | undefined;
  serviceTokenUserAccesses_aggregate?: ServiceTokenUserAccess_Aggregate_Bool_Exp | null | undefined;
  sidebar_preferences?: Jsonb_Comparison_Exp | null | undefined;
  timezone?: String_Comparison_Exp | null | undefined;
  username?: String_Comparison_Exp | null | undefined;
  workspace_preferences?: Jsonb_Comparison_Exp | null | undefined;
};

export type Whitecard_Aggregate_Bool_Exp = {
  count?: Whitecard_Aggregate_Bool_Exp_Count | null | undefined;
};

export type Whitecard_Aggregate_Bool_Exp_Count = {
  arguments?: Array<Whitecard_Select_Column> | null | undefined;
  distinct?: boolean | null | undefined;
  filter?: Whitecard_Bool_Exp | null | undefined;
  predicate: Int_Comparison_Exp;
};

/** Boolean expression to filter rows from the table "rolodex_whitecard". All fields are combined with a logical 'AND'. */
export type Whitecard_Bool_Exp = {
  _and?: Array<Whitecard_Bool_Exp> | null | undefined;
  _not?: Whitecard_Bool_Exp | null | undefined;
  _or?: Array<Whitecard_Bool_Exp> | null | undefined;
  description?: String_Comparison_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  issued?: Timestamptz_Comparison_Exp | null | undefined;
  project?: Project_Bool_Exp | null | undefined;
  projectId?: Bigint_Comparison_Exp | null | undefined;
  title?: String_Comparison_Exp | null | undefined;
};

/** select columns of table "rolodex_whitecard" */
export type Whitecard_Select_Column =
  /** column name */
  | 'description'
  /** column name */
  | 'id'
  /** column name */
  | 'issued'
  /** column name */
  | 'projectId'
  /** column name */
  | 'title';

/** Boolean expression to filter rows from the table "shepherd_whoisstatus". All fields are combined with a logical 'AND'. */
export type WhoisStatus_Bool_Exp = {
  _and?: Array<WhoisStatus_Bool_Exp> | null | undefined;
  _not?: WhoisStatus_Bool_Exp | null | undefined;
  _or?: Array<WhoisStatus_Bool_Exp> | null | undefined;
  domains?: Domain_Bool_Exp | null | undefined;
  domains_aggregate?: Domain_Aggregate_Bool_Exp | null | undefined;
  id?: Bigint_Comparison_Exp | null | undefined;
  whoisStatus?: String_Comparison_Exp | null | undefined;
};

export type Get_FindingQueryVariables = Exact<{
  id: number;
}>;


export type Get_FindingQuery = { finding_by_pk: { title: string, description: string, impact: string, mitigation: string, replication_steps: string, hostDetectionTechniques: string, networkDetectionTechniques: string, references: string, findingGuidance: string, cvssScore: number | null, cvssVector: string, findingTypeId: number, extraFields: Record<string, unknown>, severity: { id: number } } | null, tags: { tags: Array<string> }, extraFieldSpec: Array<{ internalName: string, type: string }> };

export type Set_FindingMutationVariables = Exact<{
  id: number;
  set: Finding_Set_Input;
  tags: Array<string> | string;
}>;


export type Set_FindingMutation = { update_finding_by_pk: { id: number } | null, setTags: { tags: Array<string> } };

export type Get_ObservationQueryVariables = Exact<{
  id: number;
}>;


export type Get_ObservationQuery = { observation_by_pk: { title: string, description: string, extraFields: Record<string, unknown> } | null, tags: { tags: Array<string> }, extraFieldSpec: Array<{ internalName: string, type: string }> };

export type Set_ObservationMutationVariables = Exact<{
  id: number;
  title: string;
  description: string;
  tags: Array<string> | string;
  extraFields: Record<string, unknown>;
}>;


export type Set_ObservationMutation = { update_observation_by_pk: { id: number } | null, setTags: { tags: Array<string> } };

export type Get_ProjectQueryVariables = Exact<{
  id: number;
}>;


export type Get_ProjectQuery = { project_by_pk: { collab_note: string | null } | null };

export type Set_ProjectMutationVariables = Exact<{
  id: number;
  collabNote: string;
}>;


export type Set_ProjectMutation = { update_project_by_pk: { id: number } | null };

export type Get_ReportQueryVariables = Exact<{
  id: number;
}>;


export type Get_ReportQuery = { report_by_pk: { extraFields: Record<string, unknown> } | null, extraFieldSpec: Array<{ internalName: string, type: string }> };

export type EviMutationVariables = Exact<{
  id: number;
  extraFields: Record<string, unknown>;
}>;


export type EviMutation = { update_report_by_pk: { id: number } | null };

export type Get_Report_Finding_LinkQueryVariables = Exact<{
  id: number;
}>;


export type Get_Report_Finding_LinkQuery = { reportedFinding_by_pk: { title: string, description: string, impact: string, mitigation: string, replication_steps: string, hostDetectionTechniques: string, networkDetectionTechniques: string, references: string, findingGuidance: string, cvssScore: number | null, cvssVector: string, findingTypeId: number, affectedEntities: string, extraFields: Record<string, unknown>, severity: { id: number } } | null, tags: { tags: Array<string> }, extraFieldSpec: Array<{ internalName: string, type: string }> };

export type Set_Report_Finding_LinkMutationVariables = Exact<{
  id: number;
  set: ReportedFinding_Set_Input;
  tags: Array<string> | string;
}>;


export type Set_Report_Finding_LinkMutation = { update_reportedFinding_by_pk: { id: number } | null, setTags: { tags: Array<string> } };

export type Get_Report_Observation_LinkQueryVariables = Exact<{
  id: number;
}>;


export type Get_Report_Observation_LinkQuery = { reportedObservation_by_pk: { title: string, description: string, extraFields: Record<string, unknown> } | null, tags: { tags: Array<string> }, extraFieldSpec: Array<{ internalName: string, type: string }> };

export type Set_Report_Observation_LinkMutationVariables = Exact<{
  id: number;
  title: string;
  description: string;
  tags: Array<string> | string;
  extraFields: Record<string, unknown>;
}>;


export type Set_Report_Observation_LinkMutation = { update_reportedObservation_by_pk: { id: number } | null, setTags: { tags: Array<string> } };

export type Get_Finding_TypesQueryVariables = Exact<{ [key: string]: never; }>;


export type Get_Finding_TypesQuery = { findingType: Array<{ id: number, findingType: string }> };

export type Get_SeveritiesQueryVariables = Exact<{ [key: string]: never; }>;


export type Get_SeveritiesQuery = { findingSeverity: Array<{ id: number, severity: string }> };

export type Query_EvidenceQueryVariables = Exact<{
  where: Evidence_Bool_Exp;
}>;


export type Query_EvidenceQuery = { evidence: Array<{ id: number, caption: string, description: string, friendlyName: string, document: string }> };


export const Get_FindingDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_FINDING"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"finding_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"title"}},{"kind":"Field","name":{"kind":"Name","value":"description"}},{"kind":"Field","name":{"kind":"Name","value":"impact"}},{"kind":"Field","name":{"kind":"Name","value":"mitigation"}},{"kind":"Field","name":{"kind":"Name","value":"replication_steps"}},{"kind":"Field","name":{"kind":"Name","value":"hostDetectionTechniques"}},{"kind":"Field","name":{"kind":"Name","value":"networkDetectionTechniques"}},{"kind":"Field","name":{"kind":"Name","value":"references"}},{"kind":"Field","name":{"kind":"Name","value":"findingGuidance"}},{"kind":"Field","name":{"kind":"Name","value":"cvssScore"}},{"kind":"Field","name":{"kind":"Name","value":"cvssVector"}},{"kind":"Field","name":{"kind":"Name","value":"severity"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"findingTypeId"}},{"kind":"Field","name":{"kind":"Name","value":"extraFields"}}]}},{"kind":"Field","name":{"kind":"Name","value":"tags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"finding","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}},{"kind":"Field","name":{"kind":"Name","value":"extraFieldSpec"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"targetModel"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"_eq"},"value":{"kind":"StringValue","value":"reporting.Finding","block":false}}]}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"internalName"}},{"kind":"Field","name":{"kind":"Name","value":"type"}}]}}]}}]} as unknown as DocumentNode<Get_FindingQuery, Get_FindingQueryVariables>;
export const Set_FindingDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SET_FINDING"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"set"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"finding_set_input"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"tags"}},"type":{"kind":"NonNullType","type":{"kind":"ListType","type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_finding_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"Variable","name":{"kind":"Name","value":"set"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"setTags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"finding","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}},{"kind":"Argument","name":{"kind":"Name","value":"tags"},"value":{"kind":"Variable","name":{"kind":"Name","value":"tags"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}}]}}]} as unknown as DocumentNode<Set_FindingMutation, Set_FindingMutationVariables>;
export const Get_ObservationDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_OBSERVATION"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"observation_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"title"}},{"kind":"Field","name":{"kind":"Name","value":"description"}},{"kind":"Field","name":{"kind":"Name","value":"extraFields"}}]}},{"kind":"Field","name":{"kind":"Name","value":"tags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"observation","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}},{"kind":"Field","name":{"kind":"Name","value":"extraFieldSpec"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"targetModel"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"_eq"},"value":{"kind":"StringValue","value":"reporting.Observation","block":false}}]}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"internalName"}},{"kind":"Field","name":{"kind":"Name","value":"type"}}]}}]}}]} as unknown as DocumentNode<Get_ObservationQuery, Get_ObservationQueryVariables>;
export const Set_ObservationDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SET_OBSERVATION"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"title"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"description"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"tags"}},"type":{"kind":"NonNullType","type":{"kind":"ListType","type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"jsonb"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_observation_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"title"},"value":{"kind":"Variable","name":{"kind":"Name","value":"title"}}},{"kind":"ObjectField","name":{"kind":"Name","value":"description"},"value":{"kind":"Variable","name":{"kind":"Name","value":"description"}}},{"kind":"ObjectField","name":{"kind":"Name","value":"extraFields"},"value":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"setTags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"observation","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}},{"kind":"Argument","name":{"kind":"Name","value":"tags"},"value":{"kind":"Variable","name":{"kind":"Name","value":"tags"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}}]}}]} as unknown as DocumentNode<Set_ObservationMutation, Set_ObservationMutationVariables>;
export const Get_ProjectDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_PROJECT"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"project_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"collab_note"}}]}}]}}]} as unknown as DocumentNode<Get_ProjectQuery, Get_ProjectQueryVariables>;
export const Set_ProjectDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SET_PROJECT"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"collabNote"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_project_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"collab_note"},"value":{"kind":"Variable","name":{"kind":"Name","value":"collabNote"}}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}}]}}]} as unknown as DocumentNode<Set_ProjectMutation, Set_ProjectMutationVariables>;
export const Get_ReportDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_REPORT"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"report_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"extraFields"}}]}},{"kind":"Field","name":{"kind":"Name","value":"extraFieldSpec"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"targetModel"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"_eq"},"value":{"kind":"StringValue","value":"reporting.Report","block":false}}]}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"internalName"}},{"kind":"Field","name":{"kind":"Name","value":"type"}}]}}]}}]} as unknown as DocumentNode<Get_ReportQuery, Get_ReportQueryVariables>;
export const EviDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"evi"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"jsonb"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_report_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"extraFields"},"value":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}}]}}]} as unknown as DocumentNode<EviMutation, EviMutationVariables>;
export const Get_Report_Finding_LinkDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_REPORT_FINDING_LINK"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"reportedFinding_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"title"}},{"kind":"Field","name":{"kind":"Name","value":"description"}},{"kind":"Field","name":{"kind":"Name","value":"impact"}},{"kind":"Field","name":{"kind":"Name","value":"mitigation"}},{"kind":"Field","name":{"kind":"Name","value":"replication_steps"}},{"kind":"Field","name":{"kind":"Name","value":"hostDetectionTechniques"}},{"kind":"Field","name":{"kind":"Name","value":"networkDetectionTechniques"}},{"kind":"Field","name":{"kind":"Name","value":"references"}},{"kind":"Field","name":{"kind":"Name","value":"findingGuidance"}},{"kind":"Field","name":{"kind":"Name","value":"cvssScore"}},{"kind":"Field","name":{"kind":"Name","value":"cvssVector"}},{"kind":"Field","name":{"kind":"Name","value":"severity"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"findingTypeId"}},{"kind":"Field","name":{"kind":"Name","value":"affectedEntities"}},{"kind":"Field","name":{"kind":"Name","value":"extraFields"}}]}},{"kind":"Field","name":{"kind":"Name","value":"tags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"report_finding_link","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}},{"kind":"Field","name":{"kind":"Name","value":"extraFieldSpec"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"targetModel"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"_eq"},"value":{"kind":"StringValue","value":"reporting.Finding","block":false}}]}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"internalName"}},{"kind":"Field","name":{"kind":"Name","value":"type"}}]}}]}}]} as unknown as DocumentNode<Get_Report_Finding_LinkQuery, Get_Report_Finding_LinkQueryVariables>;
export const Set_Report_Finding_LinkDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SET_REPORT_FINDING_LINK"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"set"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"reportedFinding_set_input"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"tags"}},"type":{"kind":"NonNullType","type":{"kind":"ListType","type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_reportedFinding_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"Variable","name":{"kind":"Name","value":"set"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"setTags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"report_finding_link","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}},{"kind":"Argument","name":{"kind":"Name","value":"tags"},"value":{"kind":"Variable","name":{"kind":"Name","value":"tags"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}}]}}]} as unknown as DocumentNode<Set_Report_Finding_LinkMutation, Set_Report_Finding_LinkMutationVariables>;
export const Get_Report_Observation_LinkDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_REPORT_OBSERVATION_LINK"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"reportedObservation_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"title"}},{"kind":"Field","name":{"kind":"Name","value":"description"}},{"kind":"Field","name":{"kind":"Name","value":"extraFields"}}]}},{"kind":"Field","name":{"kind":"Name","value":"tags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"report_observation_link","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}},{"kind":"Field","name":{"kind":"Name","value":"extraFieldSpec"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"targetModel"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"_eq"},"value":{"kind":"StringValue","value":"reporting.Observation","block":false}}]}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"internalName"}},{"kind":"Field","name":{"kind":"Name","value":"type"}}]}}]}}]} as unknown as DocumentNode<Get_Report_Observation_LinkQuery, Get_Report_Observation_LinkQueryVariables>;
export const Set_Report_Observation_LinkDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"mutation","name":{"kind":"Name","value":"SET_REPORT_OBSERVATION_LINK"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"id"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"bigint"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"title"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"description"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"tags"}},"type":{"kind":"NonNullType","type":{"kind":"ListType","type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"String"}}}}}},{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"jsonb"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"update_reportedObservation_by_pk"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"pk_columns"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}}]}},{"kind":"Argument","name":{"kind":"Name","value":"_set"},"value":{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"title"},"value":{"kind":"Variable","name":{"kind":"Name","value":"title"}}},{"kind":"ObjectField","name":{"kind":"Name","value":"description"},"value":{"kind":"Variable","name":{"kind":"Name","value":"description"}}},{"kind":"ObjectField","name":{"kind":"Name","value":"extraFields"},"value":{"kind":"Variable","name":{"kind":"Name","value":"extraFields"}}}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}}]}},{"kind":"Field","name":{"kind":"Name","value":"setTags"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"model"},"value":{"kind":"StringValue","value":"report_observation_link","block":false}},{"kind":"Argument","name":{"kind":"Name","value":"id"},"value":{"kind":"Variable","name":{"kind":"Name","value":"id"}}},{"kind":"Argument","name":{"kind":"Name","value":"tags"},"value":{"kind":"Variable","name":{"kind":"Name","value":"tags"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"tags"}}]}}]}}]} as unknown as DocumentNode<Set_Report_Observation_LinkMutation, Set_Report_Observation_LinkMutationVariables>;
export const Get_Finding_TypesDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_FINDING_TYPES"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"findingType"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"order_by"},"value":{"kind":"ListValue","values":[{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"EnumValue","value":"asc"}}]}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}},{"kind":"Field","name":{"kind":"Name","value":"findingType"}}]}}]}}]} as unknown as DocumentNode<Get_Finding_TypesQuery, Get_Finding_TypesQueryVariables>;
export const Get_SeveritiesDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"GET_SEVERITIES"},"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"findingSeverity"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"order_by"},"value":{"kind":"ListValue","values":[{"kind":"ObjectValue","fields":[{"kind":"ObjectField","name":{"kind":"Name","value":"id"},"value":{"kind":"EnumValue","value":"asc"}}]}]}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}},{"kind":"Field","name":{"kind":"Name","value":"severity"}}]}}]}}]} as unknown as DocumentNode<Get_SeveritiesQuery, Get_SeveritiesQueryVariables>;
export const Query_EvidenceDocument = {"kind":"Document","definitions":[{"kind":"OperationDefinition","operation":"query","name":{"kind":"Name","value":"QUERY_EVIDENCE"},"variableDefinitions":[{"kind":"VariableDefinition","variable":{"kind":"Variable","name":{"kind":"Name","value":"where"}},"type":{"kind":"NonNullType","type":{"kind":"NamedType","name":{"kind":"Name","value":"evidence_bool_exp"}}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"evidence"},"arguments":[{"kind":"Argument","name":{"kind":"Name","value":"where"},"value":{"kind":"Variable","name":{"kind":"Name","value":"where"}}}],"selectionSet":{"kind":"SelectionSet","selections":[{"kind":"Field","name":{"kind":"Name","value":"id"}},{"kind":"Field","name":{"kind":"Name","value":"caption"}},{"kind":"Field","name":{"kind":"Name","value":"description"}},{"kind":"Field","name":{"kind":"Name","value":"friendlyName"}},{"kind":"Field","name":{"kind":"Name","value":"document"}}]}}]}}]} as unknown as DocumentNode<Query_EvidenceQuery, Query_EvidenceQueryVariables>;