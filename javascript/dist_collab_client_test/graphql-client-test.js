import assert from "node:assert/strict";
import { createServer } from "node:http";
import { env } from "node:process";
//#region \0rolldown/runtime.js
var __defProp = Object.defineProperty;
var __exportAll = (all, no_symbols) => {
	let target = {};
	for (var name in all) __defProp(target, name, {
		get: all[name],
		enumerable: true
	});
	if (!no_symbols) __defProp(target, Symbol.toStringTag, { value: "Module" });
	return target;
};
//#endregion
//#region node_modules/tslib/tslib.es6.mjs
/******************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
var extendStatics = function(d, b) {
	extendStatics = Object.setPrototypeOf || { __proto__: [] } instanceof Array && function(d, b) {
		d.__proto__ = b;
	} || function(d, b) {
		for (var p in b) if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p];
	};
	return extendStatics(d, b);
};
function __extends(d, b) {
	if (typeof b !== "function" && b !== null) throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
	extendStatics(d, b);
	function __() {
		this.constructor = d;
	}
	d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
}
var __assign = function() {
	__assign = Object.assign || function __assign(t) {
		for (var s, i = 1, n = arguments.length; i < n; i++) {
			s = arguments[i];
			for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
		}
		return t;
	};
	return __assign.apply(this, arguments);
};
function __rest(s, e) {
	var t = {};
	for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0) t[p] = s[p];
	if (s != null && typeof Object.getOwnPropertySymbols === "function") {
		for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i])) t[p[i]] = s[p[i]];
	}
	return t;
}
function __awaiter(thisArg, _arguments, P, generator) {
	function adopt(value) {
		return value instanceof P ? value : new P(function(resolve) {
			resolve(value);
		});
	}
	return new (P || (P = Promise))(function(resolve, reject) {
		function fulfilled(value) {
			try {
				step(generator.next(value));
			} catch (e) {
				reject(e);
			}
		}
		function rejected(value) {
			try {
				step(generator["throw"](value));
			} catch (e) {
				reject(e);
			}
		}
		function step(result) {
			result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected);
		}
		step((generator = generator.apply(thisArg, _arguments || [])).next());
	});
}
function __generator(thisArg, body) {
	var _ = {
		label: 0,
		sent: function() {
			if (t[0] & 1) throw t[1];
			return t[1];
		},
		trys: [],
		ops: []
	}, f, y, t, g = Object.create((typeof Iterator === "function" ? Iterator : Object).prototype);
	return g.next = verb(0), g["throw"] = verb(1), g["return"] = verb(2), typeof Symbol === "function" && (g[Symbol.iterator] = function() {
		return this;
	}), g;
	function verb(n) {
		return function(v) {
			return step([n, v]);
		};
	}
	function step(op) {
		if (f) throw new TypeError("Generator is already executing.");
		while (g && (g = 0, op[0] && (_ = 0)), _) try {
			if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
			if (y = 0, t) op = [op[0] & 2, t.value];
			switch (op[0]) {
				case 0:
				case 1:
					t = op;
					break;
				case 4:
					_.label++;
					return {
						value: op[1],
						done: false
					};
				case 5:
					_.label++;
					y = op[1];
					op = [0];
					continue;
				case 7:
					op = _.ops.pop();
					_.trys.pop();
					continue;
				default:
					if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) {
						_ = 0;
						continue;
					}
					if (op[0] === 3 && (!t || op[1] > t[0] && op[1] < t[3])) {
						_.label = op[1];
						break;
					}
					if (op[0] === 6 && _.label < t[1]) {
						_.label = t[1];
						t = op;
						break;
					}
					if (t && _.label < t[2]) {
						_.label = t[2];
						_.ops.push(op);
						break;
					}
					if (t[2]) _.ops.pop();
					_.trys.pop();
					continue;
			}
			op = body.call(thisArg, _);
		} catch (e) {
			op = [6, e];
			y = 0;
		} finally {
			f = t = 0;
		}
		if (op[0] & 5) throw op[1];
		return {
			value: op[0] ? op[1] : void 0,
			done: true
		};
	}
}
function __spreadArray(to, from, pack) {
	if (pack || arguments.length === 2) {
		for (var i = 0, l = from.length, ar; i < l; i++) if (ar || !(i in from)) {
			if (!ar) ar = Array.prototype.slice.call(from, 0, i);
			ar[i] = from[i];
		}
	}
	return to.concat(ar || Array.prototype.slice.call(from));
}
//#endregion
//#region node_modules/ts-invariant/lib/invariant.js
var genericMessage = "Invariant Violation";
var _a = Object.setPrototypeOf, setPrototypeOf = _a === void 0 ? function(obj, proto) {
	obj.__proto__ = proto;
	return obj;
} : _a;
var InvariantError = function(_super) {
	__extends(InvariantError, _super);
	function InvariantError(message) {
		if (message === void 0) message = genericMessage;
		var _this = _super.call(this, typeof message === "number" ? genericMessage + ": " + message + " (see https://github.com/apollographql/invariant-packages)" : message) || this;
		_this.framesToPop = 1;
		_this.name = genericMessage;
		setPrototypeOf(_this, InvariantError.prototype);
		return _this;
	}
	return InvariantError;
}(Error);
function invariant$2(condition, message) {
	if (!condition) throw new InvariantError(message);
}
var verbosityLevels = [
	"debug",
	"log",
	"warn",
	"error",
	"silent"
];
var verbosityLevel = verbosityLevels.indexOf("log");
function wrapConsoleMethod(name) {
	return function() {
		if (verbosityLevels.indexOf(name) >= verbosityLevel) return (console[name] || console.log).apply(console, arguments);
	};
}
(function(invariant) {
	invariant.debug = wrapConsoleMethod("debug");
	invariant.log = wrapConsoleMethod("log");
	invariant.warn = wrapConsoleMethod("warn");
	invariant.error = wrapConsoleMethod("error");
})(invariant$2 || (invariant$2 = {}));
function setVerbosity(level) {
	var old = verbosityLevels[verbosityLevel];
	verbosityLevel = Math.max(0, verbosityLevels.indexOf(level));
	return old;
}
//#endregion
//#region node_modules/@apollo/client/version.js
var version = "3.14.0";
//#endregion
//#region node_modules/@apollo/client/utilities/globals/maybe.js
function maybe$1(thunk) {
	try {
		return thunk();
	} catch (_a) {}
}
//#endregion
//#region node_modules/@apollo/client/utilities/globals/global.js
var global_default = maybe$1(function() {
	return globalThis;
}) || maybe$1(function() {
	return window;
}) || maybe$1(function() {
	return self;
}) || maybe$1(function() {
	return global;
}) || maybe$1(function() {
	return maybe$1.constructor("return this")();
});
//#endregion
//#region node_modules/@apollo/client/utilities/common/makeUniqueId.js
var prefixCounts = /* @__PURE__ */ new Map();
function makeUniqueId(prefix) {
	var count = prefixCounts.get(prefix) || 1;
	prefixCounts.set(prefix, count + 1);
	return "".concat(prefix, ":").concat(count, ":").concat(Math.random().toString(36).slice(2));
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/stringifyForDisplay.js
function stringifyForDisplay(value, space) {
	if (space === void 0) space = 0;
	var undefId = makeUniqueId("stringifyForDisplay");
	return JSON.stringify(value, function(key, value) {
		return value === void 0 ? undefId : value;
	}, space).split(JSON.stringify(undefId)).join("<undefined>");
}
//#endregion
//#region node_modules/@apollo/client/utilities/globals/invariantWrappers.js
function wrap$2(fn) {
	return function(message) {
		var args = [];
		for (var _i = 1; _i < arguments.length; _i++) args[_i - 1] = arguments[_i];
		if (typeof message === "number") {
			var arg0 = message;
			message = getHandledErrorMsg(arg0);
			if (!message) {
				message = getFallbackErrorMsg(arg0, args);
				args = [];
			}
		}
		fn.apply(void 0, [message].concat(args));
	};
}
var invariant$1 = Object.assign(function invariant(condition, message) {
	var args = [];
	for (var _i = 2; _i < arguments.length; _i++) args[_i - 2] = arguments[_i];
	if (!condition) invariant$2(condition, getHandledErrorMsg(message, args) || getFallbackErrorMsg(message, args));
}, {
	debug: wrap$2(invariant$2.debug),
	log: wrap$2(invariant$2.log),
	warn: wrap$2(invariant$2.warn),
	error: wrap$2(invariant$2.error)
});
/**
* Returns an InvariantError.
*
* `message` can only be a string, a concatenation of strings, or a ternary statement
* that results in a string. This will be enforced on build, where the message will
* be replaced with a message number.
* String substitutions with %s are supported and will also return
* pretty-stringified objects.
* Excess `optionalParams` will be swallowed.
*/
function newInvariantError(message) {
	var optionalParams = [];
	for (var _i = 1; _i < arguments.length; _i++) optionalParams[_i - 1] = arguments[_i];
	return new InvariantError(getHandledErrorMsg(message, optionalParams) || getFallbackErrorMsg(message, optionalParams));
}
var ApolloErrorMessageHandler = Symbol.for("ApolloErrorMessageHandler_" + version);
function stringify(arg) {
	if (typeof arg == "string") return arg;
	try {
		return stringifyForDisplay(arg, 2).slice(0, 1e3);
	} catch (_a) {
		return "<non-serializable>";
	}
}
function getHandledErrorMsg(message, messageArgs) {
	if (messageArgs === void 0) messageArgs = [];
	if (!message) return;
	return global_default[ApolloErrorMessageHandler] && global_default[ApolloErrorMessageHandler](message, messageArgs.map(stringify));
}
function getFallbackErrorMsg(message, messageArgs) {
	if (messageArgs === void 0) messageArgs = [];
	if (!message) return;
	return "An error occurred! For more details, see the full error text at https://go.apollo.dev/c/err#".concat(encodeURIComponent(JSON.stringify({
		version,
		message,
		args: messageArgs.map(stringify)
	})));
}
//#endregion
//#region node_modules/graphql/jsutils/devAssert.mjs
function devAssert(condition, message) {
	if (!Boolean(condition)) throw new Error(message);
}
//#endregion
//#region node_modules/graphql/jsutils/isObjectLike.mjs
/**
* Return true if `value` is object-like. A value is object-like if it's not
* `null` and has a `typeof` result of "object".
*/
function isObjectLike(value) {
	return typeof value == "object" && value !== null;
}
//#endregion
//#region node_modules/graphql/jsutils/invariant.mjs
function invariant(condition, message) {
	if (!Boolean(condition)) throw new Error(message != null ? message : "Unexpected invariant triggered.");
}
//#endregion
//#region node_modules/graphql/language/location.mjs
var LineRegExp = /\r\n|[\n\r]/g;
/**
* Represents a location in a Source.
*/
/**
* Takes a Source and a UTF-8 character offset, and returns the corresponding
* line and column as a SourceLocation.
*/
function getLocation(source, position) {
	let lastLineStart = 0;
	let line = 1;
	for (const match of source.body.matchAll(LineRegExp)) {
		typeof match.index === "number" || invariant(false);
		if (match.index >= position) break;
		lastLineStart = match.index + match[0].length;
		line += 1;
	}
	return {
		line,
		column: position + 1 - lastLineStart
	};
}
//#endregion
//#region node_modules/graphql/language/printLocation.mjs
/**
* Render a helpful description of the location in the GraphQL Source document.
*/
function printLocation(location) {
	return printSourceLocation(location.source, getLocation(location.source, location.start));
}
/**
* Render a helpful description of the location in the GraphQL Source document.
*/
function printSourceLocation(source, sourceLocation) {
	const firstLineColumnOffset = source.locationOffset.column - 1;
	const body = "".padStart(firstLineColumnOffset) + source.body;
	const lineIndex = sourceLocation.line - 1;
	const lineOffset = source.locationOffset.line - 1;
	const lineNum = sourceLocation.line + lineOffset;
	const columnOffset = sourceLocation.line === 1 ? firstLineColumnOffset : 0;
	const columnNum = sourceLocation.column + columnOffset;
	const locationStr = `${source.name}:${lineNum}:${columnNum}\n`;
	const lines = body.split(/\r\n|[\n\r]/g);
	const locationLine = lines[lineIndex];
	if (locationLine.length > 120) {
		const subLineIndex = Math.floor(columnNum / 80);
		const subLineColumnNum = columnNum % 80;
		const subLines = [];
		for (let i = 0; i < locationLine.length; i += 80) subLines.push(locationLine.slice(i, i + 80));
		return locationStr + printPrefixedLines([
			[`${lineNum} |`, subLines[0]],
			...subLines.slice(1, subLineIndex + 1).map((subLine) => ["|", subLine]),
			["|", "^".padStart(subLineColumnNum)],
			["|", subLines[subLineIndex + 1]]
		]);
	}
	return locationStr + printPrefixedLines([
		[`${lineNum - 1} |`, lines[lineIndex - 1]],
		[`${lineNum} |`, locationLine],
		["|", "^".padStart(columnNum)],
		[`${lineNum + 1} |`, lines[lineIndex + 1]]
	]);
}
function printPrefixedLines(lines) {
	const existingLines = lines.filter(([_, line]) => line !== void 0);
	const padLen = Math.max(...existingLines.map(([prefix]) => prefix.length));
	return existingLines.map(([prefix, line]) => prefix.padStart(padLen) + (line ? " " + line : "")).join("\n");
}
//#endregion
//#region node_modules/graphql/error/GraphQLError.mjs
function toNormalizedOptions(args) {
	const firstArg = args[0];
	if (firstArg == null || "kind" in firstArg || "length" in firstArg) return {
		nodes: firstArg,
		source: args[1],
		positions: args[2],
		path: args[3],
		originalError: args[4],
		extensions: args[5]
	};
	return firstArg;
}
/**
* A GraphQLError describes an Error found during the parse, validate, or
* execute phases of performing a GraphQL operation. In addition to a message
* and stack trace, it also includes information about the locations in a
* GraphQL document and/or execution result that correspond to the Error.
*/
var GraphQLError = class GraphQLError extends Error {
	/**
	* An array of `{ line, column }` locations within the source GraphQL document
	* which correspond to this error.
	*
	* Errors during validation often contain multiple locations, for example to
	* point out two things with the same name. Errors during execution include a
	* single location, the field which produced the error.
	*
	* Enumerable, and appears in the result of JSON.stringify().
	*/
	/**
	* An array describing the JSON-path into the execution response which
	* corresponds to this error. Only included for errors during execution.
	*
	* Enumerable, and appears in the result of JSON.stringify().
	*/
	/**
	* An array of GraphQL AST Nodes corresponding to this error.
	*/
	/**
	* The source GraphQL document for the first location of this error.
	*
	* Note that if this Error represents more than one node, the source may not
	* represent nodes after the first node.
	*/
	/**
	* An array of character offsets within the source GraphQL document
	* which correspond to this error.
	*/
	/**
	* The original error thrown from a field resolver during execution.
	*/
	/**
	* Extension fields to add to the formatted error.
	*/
	/**
	* @deprecated Please use the `GraphQLErrorOptions` constructor overload instead.
	*/
	constructor(message, ...rawArgs) {
		var _this$nodes, _nodeLocations$, _ref;
		const { nodes, source, positions, path, originalError, extensions } = toNormalizedOptions(rawArgs);
		super(message);
		this.name = "GraphQLError";
		this.path = path !== null && path !== void 0 ? path : void 0;
		this.originalError = originalError !== null && originalError !== void 0 ? originalError : void 0;
		this.nodes = undefinedIfEmpty(Array.isArray(nodes) ? nodes : nodes ? [nodes] : void 0);
		const nodeLocations = undefinedIfEmpty((_this$nodes = this.nodes) === null || _this$nodes === void 0 ? void 0 : _this$nodes.map((node) => node.loc).filter((loc) => loc != null));
		this.source = source !== null && source !== void 0 ? source : nodeLocations === null || nodeLocations === void 0 ? void 0 : (_nodeLocations$ = nodeLocations[0]) === null || _nodeLocations$ === void 0 ? void 0 : _nodeLocations$.source;
		this.positions = positions !== null && positions !== void 0 ? positions : nodeLocations === null || nodeLocations === void 0 ? void 0 : nodeLocations.map((loc) => loc.start);
		this.locations = positions && source ? positions.map((pos) => getLocation(source, pos)) : nodeLocations === null || nodeLocations === void 0 ? void 0 : nodeLocations.map((loc) => getLocation(loc.source, loc.start));
		const originalExtensions = isObjectLike(originalError === null || originalError === void 0 ? void 0 : originalError.extensions) ? originalError === null || originalError === void 0 ? void 0 : originalError.extensions : void 0;
		this.extensions = (_ref = extensions !== null && extensions !== void 0 ? extensions : originalExtensions) !== null && _ref !== void 0 ? _ref : Object.create(null);
		Object.defineProperties(this, {
			message: {
				writable: true,
				enumerable: true
			},
			name: { enumerable: false },
			nodes: { enumerable: false },
			source: { enumerable: false },
			positions: { enumerable: false },
			originalError: { enumerable: false }
		});
		/* c8 ignore start */
		if (originalError !== null && originalError !== void 0 && originalError.stack) Object.defineProperty(this, "stack", {
			value: originalError.stack,
			writable: true,
			configurable: true
		});
		else if (Error.captureStackTrace) Error.captureStackTrace(this, GraphQLError);
		else Object.defineProperty(this, "stack", {
			value: Error().stack,
			writable: true,
			configurable: true
		});
		/* c8 ignore stop */
	}
	get [Symbol.toStringTag]() {
		return "GraphQLError";
	}
	toString() {
		let output = this.message;
		if (this.nodes) {
			for (const node of this.nodes) if (node.loc) output += "\n\n" + printLocation(node.loc);
		} else if (this.source && this.locations) for (const location of this.locations) output += "\n\n" + printSourceLocation(this.source, location);
		return output;
	}
	toJSON() {
		const formattedError = { message: this.message };
		if (this.locations != null) formattedError.locations = this.locations;
		if (this.path != null) formattedError.path = this.path;
		if (this.extensions != null && Object.keys(this.extensions).length > 0) formattedError.extensions = this.extensions;
		return formattedError;
	}
};
function undefinedIfEmpty(array) {
	return array === void 0 || array.length === 0 ? void 0 : array;
}
//#endregion
//#region node_modules/graphql/error/syntaxError.mjs
/**
* Produces a GraphQLError representing a syntax error, containing useful
* descriptive information about the syntax error's position in the source.
*/
function syntaxError(source, position, description) {
	return new GraphQLError(`Syntax Error: ${description}`, {
		source,
		positions: [position]
	});
}
//#endregion
//#region node_modules/graphql/language/ast.mjs
/**
* Contains a range of UTF-8 character offsets and token references that
* identify the region of the source from which the AST derived.
*/
var Location = class {
	/**
	* The character offset at which this Node begins.
	*/
	/**
	* The character offset at which this Node ends.
	*/
	/**
	* The Token at which this Node begins.
	*/
	/**
	* The Token at which this Node ends.
	*/
	/**
	* The Source document the AST represents.
	*/
	constructor(startToken, endToken, source) {
		this.start = startToken.start;
		this.end = endToken.end;
		this.startToken = startToken;
		this.endToken = endToken;
		this.source = source;
	}
	get [Symbol.toStringTag]() {
		return "Location";
	}
	toJSON() {
		return {
			start: this.start,
			end: this.end
		};
	}
};
/**
* Represents a range of characters represented by a lexical token
* within a Source.
*/
var Token = class {
	/**
	* The kind of Token.
	*/
	/**
	* The character offset at which this Node begins.
	*/
	/**
	* The character offset at which this Node ends.
	*/
	/**
	* The 1-indexed line number on which this Token appears.
	*/
	/**
	* The 1-indexed column number at which this Token begins.
	*/
	/**
	* For non-punctuation tokens, represents the interpreted value of the token.
	*
	* Note: is undefined for punctuation tokens, but typed as string for
	* convenience in the parser.
	*/
	/**
	* Tokens exist as nodes in a double-linked-list amongst all tokens
	* including ignored tokens. <SOF> is always the first node and <EOF>
	* the last.
	*/
	constructor(kind, start, end, line, column, value) {
		this.kind = kind;
		this.start = start;
		this.end = end;
		this.line = line;
		this.column = column;
		this.value = value;
		this.prev = null;
		this.next = null;
	}
	get [Symbol.toStringTag]() {
		return "Token";
	}
	toJSON() {
		return {
			kind: this.kind,
			value: this.value,
			line: this.line,
			column: this.column
		};
	}
};
/**
* The list of all possible AST node types.
*/
/**
* @internal
*/
var QueryDocumentKeys = {
	Name: [],
	Document: ["definitions"],
	OperationDefinition: [
		"name",
		"variableDefinitions",
		"directives",
		"selectionSet"
	],
	VariableDefinition: [
		"variable",
		"type",
		"defaultValue",
		"directives"
	],
	Variable: ["name"],
	SelectionSet: ["selections"],
	Field: [
		"alias",
		"name",
		"arguments",
		"directives",
		"selectionSet"
	],
	Argument: ["name", "value"],
	FragmentSpread: ["name", "directives"],
	InlineFragment: [
		"typeCondition",
		"directives",
		"selectionSet"
	],
	FragmentDefinition: [
		"name",
		"variableDefinitions",
		"typeCondition",
		"directives",
		"selectionSet"
	],
	IntValue: [],
	FloatValue: [],
	StringValue: [],
	BooleanValue: [],
	NullValue: [],
	EnumValue: [],
	ListValue: ["values"],
	ObjectValue: ["fields"],
	ObjectField: ["name", "value"],
	Directive: ["name", "arguments"],
	NamedType: ["name"],
	ListType: ["type"],
	NonNullType: ["type"],
	SchemaDefinition: [
		"description",
		"directives",
		"operationTypes"
	],
	OperationTypeDefinition: ["type"],
	ScalarTypeDefinition: [
		"description",
		"name",
		"directives"
	],
	ObjectTypeDefinition: [
		"description",
		"name",
		"interfaces",
		"directives",
		"fields"
	],
	FieldDefinition: [
		"description",
		"name",
		"arguments",
		"type",
		"directives"
	],
	InputValueDefinition: [
		"description",
		"name",
		"type",
		"defaultValue",
		"directives"
	],
	InterfaceTypeDefinition: [
		"description",
		"name",
		"interfaces",
		"directives",
		"fields"
	],
	UnionTypeDefinition: [
		"description",
		"name",
		"directives",
		"types"
	],
	EnumTypeDefinition: [
		"description",
		"name",
		"directives",
		"values"
	],
	EnumValueDefinition: [
		"description",
		"name",
		"directives"
	],
	InputObjectTypeDefinition: [
		"description",
		"name",
		"directives",
		"fields"
	],
	DirectiveDefinition: [
		"description",
		"name",
		"arguments",
		"locations"
	],
	SchemaExtension: ["directives", "operationTypes"],
	ScalarTypeExtension: ["name", "directives"],
	ObjectTypeExtension: [
		"name",
		"interfaces",
		"directives",
		"fields"
	],
	InterfaceTypeExtension: [
		"name",
		"interfaces",
		"directives",
		"fields"
	],
	UnionTypeExtension: [
		"name",
		"directives",
		"types"
	],
	EnumTypeExtension: [
		"name",
		"directives",
		"values"
	],
	InputObjectTypeExtension: [
		"name",
		"directives",
		"fields"
	]
};
var kindValues = new Set(Object.keys(QueryDocumentKeys));
/**
* @internal
*/
function isNode(maybeNode) {
	const maybeKind = maybeNode === null || maybeNode === void 0 ? void 0 : maybeNode.kind;
	return typeof maybeKind === "string" && kindValues.has(maybeKind);
}
/** Name */
var OperationTypeNode;
(function(OperationTypeNode) {
	OperationTypeNode["QUERY"] = "query";
	OperationTypeNode["MUTATION"] = "mutation";
	OperationTypeNode["SUBSCRIPTION"] = "subscription";
})(OperationTypeNode || (OperationTypeNode = {}));
//#endregion
//#region node_modules/graphql/language/directiveLocation.mjs
/**
* The set of allowed directive location values.
*/
var DirectiveLocation;
(function(DirectiveLocation) {
	DirectiveLocation["QUERY"] = "QUERY";
	DirectiveLocation["MUTATION"] = "MUTATION";
	DirectiveLocation["SUBSCRIPTION"] = "SUBSCRIPTION";
	DirectiveLocation["FIELD"] = "FIELD";
	DirectiveLocation["FRAGMENT_DEFINITION"] = "FRAGMENT_DEFINITION";
	DirectiveLocation["FRAGMENT_SPREAD"] = "FRAGMENT_SPREAD";
	DirectiveLocation["INLINE_FRAGMENT"] = "INLINE_FRAGMENT";
	DirectiveLocation["VARIABLE_DEFINITION"] = "VARIABLE_DEFINITION";
	DirectiveLocation["SCHEMA"] = "SCHEMA";
	DirectiveLocation["SCALAR"] = "SCALAR";
	DirectiveLocation["OBJECT"] = "OBJECT";
	DirectiveLocation["FIELD_DEFINITION"] = "FIELD_DEFINITION";
	DirectiveLocation["ARGUMENT_DEFINITION"] = "ARGUMENT_DEFINITION";
	DirectiveLocation["INTERFACE"] = "INTERFACE";
	DirectiveLocation["UNION"] = "UNION";
	DirectiveLocation["ENUM"] = "ENUM";
	DirectiveLocation["ENUM_VALUE"] = "ENUM_VALUE";
	DirectiveLocation["INPUT_OBJECT"] = "INPUT_OBJECT";
	DirectiveLocation["INPUT_FIELD_DEFINITION"] = "INPUT_FIELD_DEFINITION";
})(DirectiveLocation || (DirectiveLocation = {}));
/**
* The enum type representing the directive location values.
*
* @deprecated Please use `DirectiveLocation`. Will be remove in v17.
*/
//#endregion
//#region node_modules/graphql/language/kinds.mjs
/**
* The set of allowed kind values for AST nodes.
*/
var Kind;
(function(Kind) {
	Kind["NAME"] = "Name";
	Kind["DOCUMENT"] = "Document";
	Kind["OPERATION_DEFINITION"] = "OperationDefinition";
	Kind["VARIABLE_DEFINITION"] = "VariableDefinition";
	Kind["SELECTION_SET"] = "SelectionSet";
	Kind["FIELD"] = "Field";
	Kind["ARGUMENT"] = "Argument";
	Kind["FRAGMENT_SPREAD"] = "FragmentSpread";
	Kind["INLINE_FRAGMENT"] = "InlineFragment";
	Kind["FRAGMENT_DEFINITION"] = "FragmentDefinition";
	Kind["VARIABLE"] = "Variable";
	Kind["INT"] = "IntValue";
	Kind["FLOAT"] = "FloatValue";
	Kind["STRING"] = "StringValue";
	Kind["BOOLEAN"] = "BooleanValue";
	Kind["NULL"] = "NullValue";
	Kind["ENUM"] = "EnumValue";
	Kind["LIST"] = "ListValue";
	Kind["OBJECT"] = "ObjectValue";
	Kind["OBJECT_FIELD"] = "ObjectField";
	Kind["DIRECTIVE"] = "Directive";
	Kind["NAMED_TYPE"] = "NamedType";
	Kind["LIST_TYPE"] = "ListType";
	Kind["NON_NULL_TYPE"] = "NonNullType";
	Kind["SCHEMA_DEFINITION"] = "SchemaDefinition";
	Kind["OPERATION_TYPE_DEFINITION"] = "OperationTypeDefinition";
	Kind["SCALAR_TYPE_DEFINITION"] = "ScalarTypeDefinition";
	Kind["OBJECT_TYPE_DEFINITION"] = "ObjectTypeDefinition";
	Kind["FIELD_DEFINITION"] = "FieldDefinition";
	Kind["INPUT_VALUE_DEFINITION"] = "InputValueDefinition";
	Kind["INTERFACE_TYPE_DEFINITION"] = "InterfaceTypeDefinition";
	Kind["UNION_TYPE_DEFINITION"] = "UnionTypeDefinition";
	Kind["ENUM_TYPE_DEFINITION"] = "EnumTypeDefinition";
	Kind["ENUM_VALUE_DEFINITION"] = "EnumValueDefinition";
	Kind["INPUT_OBJECT_TYPE_DEFINITION"] = "InputObjectTypeDefinition";
	Kind["DIRECTIVE_DEFINITION"] = "DirectiveDefinition";
	Kind["SCHEMA_EXTENSION"] = "SchemaExtension";
	Kind["SCALAR_TYPE_EXTENSION"] = "ScalarTypeExtension";
	Kind["OBJECT_TYPE_EXTENSION"] = "ObjectTypeExtension";
	Kind["INTERFACE_TYPE_EXTENSION"] = "InterfaceTypeExtension";
	Kind["UNION_TYPE_EXTENSION"] = "UnionTypeExtension";
	Kind["ENUM_TYPE_EXTENSION"] = "EnumTypeExtension";
	Kind["INPUT_OBJECT_TYPE_EXTENSION"] = "InputObjectTypeExtension";
})(Kind || (Kind = {}));
/**
* The enum type representing the possible kind values of AST nodes.
*
* @deprecated Please use `Kind`. Will be remove in v17.
*/
//#endregion
//#region node_modules/graphql/language/characterClasses.mjs
/**
* ```
* WhiteSpace ::
*   - "Horizontal Tab (U+0009)"
*   - "Space (U+0020)"
* ```
* @internal
*/
function isWhiteSpace(code) {
	return code === 9 || code === 32;
}
/**
* ```
* Digit :: one of
*   - `0` `1` `2` `3` `4` `5` `6` `7` `8` `9`
* ```
* @internal
*/
function isDigit(code) {
	return code >= 48 && code <= 57;
}
/**
* ```
* Letter :: one of
*   - `A` `B` `C` `D` `E` `F` `G` `H` `I` `J` `K` `L` `M`
*   - `N` `O` `P` `Q` `R` `S` `T` `U` `V` `W` `X` `Y` `Z`
*   - `a` `b` `c` `d` `e` `f` `g` `h` `i` `j` `k` `l` `m`
*   - `n` `o` `p` `q` `r` `s` `t` `u` `v` `w` `x` `y` `z`
* ```
* @internal
*/
function isLetter(code) {
	return code >= 97 && code <= 122 || code >= 65 && code <= 90;
}
/**
* ```
* NameStart ::
*   - Letter
*   - `_`
* ```
* @internal
*/
function isNameStart(code) {
	return isLetter(code) || code === 95;
}
/**
* ```
* NameContinue ::
*   - Letter
*   - Digit
*   - `_`
* ```
* @internal
*/
function isNameContinue(code) {
	return isLetter(code) || isDigit(code) || code === 95;
}
//#endregion
//#region node_modules/graphql/language/blockString.mjs
/**
* Produces the value of a block string from its parsed raw value, similar to
* CoffeeScript's block string, Python's docstring trim or Ruby's strip_heredoc.
*
* This implements the GraphQL spec's BlockStringValue() static algorithm.
*
* @internal
*/
function dedentBlockStringLines(lines) {
	var _firstNonEmptyLine2;
	let commonIndent = Number.MAX_SAFE_INTEGER;
	let firstNonEmptyLine = null;
	let lastNonEmptyLine = -1;
	for (let i = 0; i < lines.length; ++i) {
		var _firstNonEmptyLine;
		const line = lines[i];
		const indent = leadingWhitespace(line);
		if (indent === line.length) continue;
		firstNonEmptyLine = (_firstNonEmptyLine = firstNonEmptyLine) !== null && _firstNonEmptyLine !== void 0 ? _firstNonEmptyLine : i;
		lastNonEmptyLine = i;
		if (i !== 0 && indent < commonIndent) commonIndent = indent;
	}
	return lines.map((line, i) => i === 0 ? line : line.slice(commonIndent)).slice((_firstNonEmptyLine2 = firstNonEmptyLine) !== null && _firstNonEmptyLine2 !== void 0 ? _firstNonEmptyLine2 : 0, lastNonEmptyLine + 1);
}
function leadingWhitespace(str) {
	let i = 0;
	while (i < str.length && isWhiteSpace(str.charCodeAt(i))) ++i;
	return i;
}
/**
* Print a block string in the indented block form by adding a leading and
* trailing blank line. However, if a block string starts with whitespace and is
* a single-line, adding a leading blank line would strip that whitespace.
*
* @internal
*/
function printBlockString(value, options) {
	const escapedValue = value.replace(/"""/g, "\\\"\"\"");
	const lines = escapedValue.split(/\r\n|[\n\r]/g);
	const isSingleLine = lines.length === 1;
	const forceLeadingNewLine = lines.length > 1 && lines.slice(1).every((line) => line.length === 0 || isWhiteSpace(line.charCodeAt(0)));
	const hasTrailingTripleQuotes = escapedValue.endsWith("\\\"\"\"");
	const hasTrailingQuote = value.endsWith("\"") && !hasTrailingTripleQuotes;
	const hasTrailingSlash = value.endsWith("\\");
	const forceTrailingNewline = hasTrailingQuote || hasTrailingSlash;
	const printAsMultipleLines = !(options !== null && options !== void 0 && options.minimize) && (!isSingleLine || value.length > 70 || forceTrailingNewline || forceLeadingNewLine || hasTrailingTripleQuotes);
	let result = "";
	const skipLeadingNewLine = isSingleLine && isWhiteSpace(value.charCodeAt(0));
	if (printAsMultipleLines && !skipLeadingNewLine || forceLeadingNewLine) result += "\n";
	result += escapedValue;
	if (printAsMultipleLines || forceTrailingNewline) result += "\n";
	return "\"\"\"" + result + "\"\"\"";
}
//#endregion
//#region node_modules/graphql/language/tokenKind.mjs
/**
* An exported enum describing the different kinds of tokens that the
* lexer emits.
*/
var TokenKind;
(function(TokenKind) {
	TokenKind["SOF"] = "<SOF>";
	TokenKind["EOF"] = "<EOF>";
	TokenKind["BANG"] = "!";
	TokenKind["DOLLAR"] = "$";
	TokenKind["AMP"] = "&";
	TokenKind["PAREN_L"] = "(";
	TokenKind["PAREN_R"] = ")";
	TokenKind["SPREAD"] = "...";
	TokenKind["COLON"] = ":";
	TokenKind["EQUALS"] = "=";
	TokenKind["AT"] = "@";
	TokenKind["BRACKET_L"] = "[";
	TokenKind["BRACKET_R"] = "]";
	TokenKind["BRACE_L"] = "{";
	TokenKind["PIPE"] = "|";
	TokenKind["BRACE_R"] = "}";
	TokenKind["NAME"] = "Name";
	TokenKind["INT"] = "Int";
	TokenKind["FLOAT"] = "Float";
	TokenKind["STRING"] = "String";
	TokenKind["BLOCK_STRING"] = "BlockString";
	TokenKind["COMMENT"] = "Comment";
})(TokenKind || (TokenKind = {}));
/**
* The enum type representing the token kinds values.
*
* @deprecated Please use `TokenKind`. Will be remove in v17.
*/
//#endregion
//#region node_modules/graphql/language/lexer.mjs
/**
* Given a Source object, creates a Lexer for that source.
* A Lexer is a stateful stream generator in that every time
* it is advanced, it returns the next token in the Source. Assuming the
* source lexes, the final Token emitted by the lexer will be of kind
* EOF, after which the lexer will repeatedly return the same EOF token
* whenever called.
*/
var Lexer = class {
	/**
	* The previously focused non-ignored token.
	*/
	/**
	* The currently focused non-ignored token.
	*/
	/**
	* The (1-indexed) line containing the current token.
	*/
	/**
	* The character offset at which the current line begins.
	*/
	constructor(source) {
		const startOfFileToken = new Token(TokenKind.SOF, 0, 0, 0, 0);
		this.source = source;
		this.lastToken = startOfFileToken;
		this.token = startOfFileToken;
		this.line = 1;
		this.lineStart = 0;
	}
	get [Symbol.toStringTag]() {
		return "Lexer";
	}
	/**
	* Advances the token stream to the next non-ignored token.
	*/
	advance() {
		this.lastToken = this.token;
		return this.token = this.lookahead();
	}
	/**
	* Looks ahead and returns the next non-ignored token, but does not change
	* the state of Lexer.
	*/
	lookahead() {
		let token = this.token;
		if (token.kind !== TokenKind.EOF) do
			if (token.next) token = token.next;
			else {
				const nextToken = readNextToken(this, token.end);
				token.next = nextToken;
				nextToken.prev = token;
				token = nextToken;
			}
		while (token.kind === TokenKind.COMMENT);
		return token;
	}
};
/**
* @internal
*/
function isPunctuatorTokenKind(kind) {
	return kind === TokenKind.BANG || kind === TokenKind.DOLLAR || kind === TokenKind.AMP || kind === TokenKind.PAREN_L || kind === TokenKind.PAREN_R || kind === TokenKind.SPREAD || kind === TokenKind.COLON || kind === TokenKind.EQUALS || kind === TokenKind.AT || kind === TokenKind.BRACKET_L || kind === TokenKind.BRACKET_R || kind === TokenKind.BRACE_L || kind === TokenKind.PIPE || kind === TokenKind.BRACE_R;
}
/**
* A Unicode scalar value is any Unicode code point except surrogate code
* points. In other words, the inclusive ranges of values 0x0000 to 0xD7FF and
* 0xE000 to 0x10FFFF.
*
* SourceCharacter ::
*   - "Any Unicode scalar value"
*/
function isUnicodeScalarValue(code) {
	return code >= 0 && code <= 55295 || code >= 57344 && code <= 1114111;
}
/**
* The GraphQL specification defines source text as a sequence of unicode scalar
* values (which Unicode defines to exclude surrogate code points). However
* JavaScript defines strings as a sequence of UTF-16 code units which may
* include surrogates. A surrogate pair is a valid source character as it
* encodes a supplementary code point (above U+FFFF), but unpaired surrogate
* code points are not valid source characters.
*/
function isSupplementaryCodePoint(body, location) {
	return isLeadingSurrogate(body.charCodeAt(location)) && isTrailingSurrogate(body.charCodeAt(location + 1));
}
function isLeadingSurrogate(code) {
	return code >= 55296 && code <= 56319;
}
function isTrailingSurrogate(code) {
	return code >= 56320 && code <= 57343;
}
/**
* Prints the code point (or end of file reference) at a given location in a
* source for use in error messages.
*
* Printable ASCII is printed quoted, while other points are printed in Unicode
* code point form (ie. U+1234).
*/
function printCodePointAt(lexer, location) {
	const code = lexer.source.body.codePointAt(location);
	if (code === void 0) return TokenKind.EOF;
	else if (code >= 32 && code <= 126) {
		const char = String.fromCodePoint(code);
		return char === "\"" ? "'\"'" : `"${char}"`;
	}
	return "U+" + code.toString(16).toUpperCase().padStart(4, "0");
}
/**
* Create a token with line and column location information.
*/
function createToken(lexer, kind, start, end, value) {
	const line = lexer.line;
	return new Token(kind, start, end, line, 1 + start - lexer.lineStart, value);
}
/**
* Gets the next token from the source starting at the given position.
*
* This skips over whitespace until it finds the next lexable token, then lexes
* punctuators immediately or calls the appropriate helper function for more
* complicated tokens.
*/
function readNextToken(lexer, start) {
	const body = lexer.source.body;
	const bodyLength = body.length;
	let position = start;
	while (position < bodyLength) {
		const code = body.charCodeAt(position);
		switch (code) {
			case 65279:
			case 9:
			case 32:
			case 44:
				++position;
				continue;
			case 10:
				++position;
				++lexer.line;
				lexer.lineStart = position;
				continue;
			case 13:
				if (body.charCodeAt(position + 1) === 10) position += 2;
				else ++position;
				++lexer.line;
				lexer.lineStart = position;
				continue;
			case 35: return readComment(lexer, position);
			case 33: return createToken(lexer, TokenKind.BANG, position, position + 1);
			case 36: return createToken(lexer, TokenKind.DOLLAR, position, position + 1);
			case 38: return createToken(lexer, TokenKind.AMP, position, position + 1);
			case 40: return createToken(lexer, TokenKind.PAREN_L, position, position + 1);
			case 41: return createToken(lexer, TokenKind.PAREN_R, position, position + 1);
			case 46:
				if (body.charCodeAt(position + 1) === 46 && body.charCodeAt(position + 2) === 46) return createToken(lexer, TokenKind.SPREAD, position, position + 3);
				break;
			case 58: return createToken(lexer, TokenKind.COLON, position, position + 1);
			case 61: return createToken(lexer, TokenKind.EQUALS, position, position + 1);
			case 64: return createToken(lexer, TokenKind.AT, position, position + 1);
			case 91: return createToken(lexer, TokenKind.BRACKET_L, position, position + 1);
			case 93: return createToken(lexer, TokenKind.BRACKET_R, position, position + 1);
			case 123: return createToken(lexer, TokenKind.BRACE_L, position, position + 1);
			case 124: return createToken(lexer, TokenKind.PIPE, position, position + 1);
			case 125: return createToken(lexer, TokenKind.BRACE_R, position, position + 1);
			case 34:
				if (body.charCodeAt(position + 1) === 34 && body.charCodeAt(position + 2) === 34) return readBlockString(lexer, position);
				return readString(lexer, position);
		}
		if (isDigit(code) || code === 45) return readNumber(lexer, position, code);
		if (isNameStart(code)) return readName(lexer, position);
		throw syntaxError(lexer.source, position, code === 39 ? "Unexpected single quote character ('), did you mean to use a double quote (\")?" : isUnicodeScalarValue(code) || isSupplementaryCodePoint(body, position) ? `Unexpected character: ${printCodePointAt(lexer, position)}.` : `Invalid character: ${printCodePointAt(lexer, position)}.`);
	}
	return createToken(lexer, TokenKind.EOF, bodyLength, bodyLength);
}
/**
* Reads a comment token from the source file.
*
* ```
* Comment :: # CommentChar* [lookahead != CommentChar]
*
* CommentChar :: SourceCharacter but not LineTerminator
* ```
*/
function readComment(lexer, start) {
	const body = lexer.source.body;
	const bodyLength = body.length;
	let position = start + 1;
	while (position < bodyLength) {
		const code = body.charCodeAt(position);
		if (code === 10 || code === 13) break;
		if (isUnicodeScalarValue(code)) ++position;
		else if (isSupplementaryCodePoint(body, position)) position += 2;
		else break;
	}
	return createToken(lexer, TokenKind.COMMENT, start, position, body.slice(start + 1, position));
}
/**
* Reads a number token from the source file, either a FloatValue or an IntValue
* depending on whether a FractionalPart or ExponentPart is encountered.
*
* ```
* IntValue :: IntegerPart [lookahead != {Digit, `.`, NameStart}]
*
* IntegerPart ::
*   - NegativeSign? 0
*   - NegativeSign? NonZeroDigit Digit*
*
* NegativeSign :: -
*
* NonZeroDigit :: Digit but not `0`
*
* FloatValue ::
*   - IntegerPart FractionalPart ExponentPart [lookahead != {Digit, `.`, NameStart}]
*   - IntegerPart FractionalPart [lookahead != {Digit, `.`, NameStart}]
*   - IntegerPart ExponentPart [lookahead != {Digit, `.`, NameStart}]
*
* FractionalPart :: . Digit+
*
* ExponentPart :: ExponentIndicator Sign? Digit+
*
* ExponentIndicator :: one of `e` `E`
*
* Sign :: one of + -
* ```
*/
function readNumber(lexer, start, firstCode) {
	const body = lexer.source.body;
	let position = start;
	let code = firstCode;
	let isFloat = false;
	if (code === 45) code = body.charCodeAt(++position);
	if (code === 48) {
		code = body.charCodeAt(++position);
		if (isDigit(code)) throw syntaxError(lexer.source, position, `Invalid number, unexpected digit after 0: ${printCodePointAt(lexer, position)}.`);
	} else {
		position = readDigits(lexer, position, code);
		code = body.charCodeAt(position);
	}
	if (code === 46) {
		isFloat = true;
		code = body.charCodeAt(++position);
		position = readDigits(lexer, position, code);
		code = body.charCodeAt(position);
	}
	if (code === 69 || code === 101) {
		isFloat = true;
		code = body.charCodeAt(++position);
		if (code === 43 || code === 45) code = body.charCodeAt(++position);
		position = readDigits(lexer, position, code);
		code = body.charCodeAt(position);
	}
	if (code === 46 || isNameStart(code)) throw syntaxError(lexer.source, position, `Invalid number, expected digit but got: ${printCodePointAt(lexer, position)}.`);
	return createToken(lexer, isFloat ? TokenKind.FLOAT : TokenKind.INT, start, position, body.slice(start, position));
}
/**
* Returns the new position in the source after reading one or more digits.
*/
function readDigits(lexer, start, firstCode) {
	if (!isDigit(firstCode)) throw syntaxError(lexer.source, start, `Invalid number, expected digit but got: ${printCodePointAt(lexer, start)}.`);
	const body = lexer.source.body;
	let position = start + 1;
	while (isDigit(body.charCodeAt(position))) ++position;
	return position;
}
/**
* Reads a single-quote string token from the source file.
*
* ```
* StringValue ::
*   - `""` [lookahead != `"`]
*   - `"` StringCharacter+ `"`
*
* StringCharacter ::
*   - SourceCharacter but not `"` or `\` or LineTerminator
*   - `\u` EscapedUnicode
*   - `\` EscapedCharacter
*
* EscapedUnicode ::
*   - `{` HexDigit+ `}`
*   - HexDigit HexDigit HexDigit HexDigit
*
* EscapedCharacter :: one of `"` `\` `/` `b` `f` `n` `r` `t`
* ```
*/
function readString(lexer, start) {
	const body = lexer.source.body;
	const bodyLength = body.length;
	let position = start + 1;
	let chunkStart = position;
	let value = "";
	while (position < bodyLength) {
		const code = body.charCodeAt(position);
		if (code === 34) {
			value += body.slice(chunkStart, position);
			return createToken(lexer, TokenKind.STRING, start, position + 1, value);
		}
		if (code === 92) {
			value += body.slice(chunkStart, position);
			const escape = body.charCodeAt(position + 1) === 117 ? body.charCodeAt(position + 2) === 123 ? readEscapedUnicodeVariableWidth(lexer, position) : readEscapedUnicodeFixedWidth(lexer, position) : readEscapedCharacter(lexer, position);
			value += escape.value;
			position += escape.size;
			chunkStart = position;
			continue;
		}
		if (code === 10 || code === 13) break;
		if (isUnicodeScalarValue(code)) ++position;
		else if (isSupplementaryCodePoint(body, position)) position += 2;
		else throw syntaxError(lexer.source, position, `Invalid character within String: ${printCodePointAt(lexer, position)}.`);
	}
	throw syntaxError(lexer.source, position, "Unterminated string.");
}
function readEscapedUnicodeVariableWidth(lexer, position) {
	const body = lexer.source.body;
	let point = 0;
	let size = 3;
	while (size < 12) {
		const code = body.charCodeAt(position + size++);
		if (code === 125) {
			if (size < 5 || !isUnicodeScalarValue(point)) break;
			return {
				value: String.fromCodePoint(point),
				size
			};
		}
		point = point << 4 | readHexDigit(code);
		if (point < 0) break;
	}
	throw syntaxError(lexer.source, position, `Invalid Unicode escape sequence: "${body.slice(position, position + size)}".`);
}
function readEscapedUnicodeFixedWidth(lexer, position) {
	const body = lexer.source.body;
	const code = read16BitHexCode(body, position + 2);
	if (isUnicodeScalarValue(code)) return {
		value: String.fromCodePoint(code),
		size: 6
	};
	if (isLeadingSurrogate(code)) {
		if (body.charCodeAt(position + 6) === 92 && body.charCodeAt(position + 7) === 117) {
			const trailingCode = read16BitHexCode(body, position + 8);
			if (isTrailingSurrogate(trailingCode)) return {
				value: String.fromCodePoint(code, trailingCode),
				size: 12
			};
		}
	}
	throw syntaxError(lexer.source, position, `Invalid Unicode escape sequence: "${body.slice(position, position + 6)}".`);
}
/**
* Reads four hexadecimal characters and returns the positive integer that 16bit
* hexadecimal string represents. For example, "000f" will return 15, and "dead"
* will return 57005.
*
* Returns a negative number if any char was not a valid hexadecimal digit.
*/
function read16BitHexCode(body, position) {
	return readHexDigit(body.charCodeAt(position)) << 12 | readHexDigit(body.charCodeAt(position + 1)) << 8 | readHexDigit(body.charCodeAt(position + 2)) << 4 | readHexDigit(body.charCodeAt(position + 3));
}
/**
* Reads a hexadecimal character and returns its positive integer value (0-15).
*
* '0' becomes 0, '9' becomes 9
* 'A' becomes 10, 'F' becomes 15
* 'a' becomes 10, 'f' becomes 15
*
* Returns -1 if the provided character code was not a valid hexadecimal digit.
*
* HexDigit :: one of
*   - `0` `1` `2` `3` `4` `5` `6` `7` `8` `9`
*   - `A` `B` `C` `D` `E` `F`
*   - `a` `b` `c` `d` `e` `f`
*/
function readHexDigit(code) {
	return code >= 48 && code <= 57 ? code - 48 : code >= 65 && code <= 70 ? code - 55 : code >= 97 && code <= 102 ? code - 87 : -1;
}
/**
* | Escaped Character | Code Point | Character Name               |
* | ----------------- | ---------- | ---------------------------- |
* | `"`               | U+0022     | double quote                 |
* | `\`               | U+005C     | reverse solidus (back slash) |
* | `/`               | U+002F     | solidus (forward slash)      |
* | `b`               | U+0008     | backspace                    |
* | `f`               | U+000C     | form feed                    |
* | `n`               | U+000A     | line feed (new line)         |
* | `r`               | U+000D     | carriage return              |
* | `t`               | U+0009     | horizontal tab               |
*/
function readEscapedCharacter(lexer, position) {
	const body = lexer.source.body;
	switch (body.charCodeAt(position + 1)) {
		case 34: return {
			value: "\"",
			size: 2
		};
		case 92: return {
			value: "\\",
			size: 2
		};
		case 47: return {
			value: "/",
			size: 2
		};
		case 98: return {
			value: "\b",
			size: 2
		};
		case 102: return {
			value: "\f",
			size: 2
		};
		case 110: return {
			value: "\n",
			size: 2
		};
		case 114: return {
			value: "\r",
			size: 2
		};
		case 116: return {
			value: "	",
			size: 2
		};
	}
	throw syntaxError(lexer.source, position, `Invalid character escape sequence: "${body.slice(position, position + 2)}".`);
}
/**
* Reads a block string token from the source file.
*
* ```
* StringValue ::
*   - `"""` BlockStringCharacter* `"""`
*
* BlockStringCharacter ::
*   - SourceCharacter but not `"""` or `\"""`
*   - `\"""`
* ```
*/
function readBlockString(lexer, start) {
	const body = lexer.source.body;
	const bodyLength = body.length;
	let lineStart = lexer.lineStart;
	let position = start + 3;
	let chunkStart = position;
	let currentLine = "";
	const blockLines = [];
	while (position < bodyLength) {
		const code = body.charCodeAt(position);
		if (code === 34 && body.charCodeAt(position + 1) === 34 && body.charCodeAt(position + 2) === 34) {
			currentLine += body.slice(chunkStart, position);
			blockLines.push(currentLine);
			const token = createToken(lexer, TokenKind.BLOCK_STRING, start, position + 3, dedentBlockStringLines(blockLines).join("\n"));
			lexer.line += blockLines.length - 1;
			lexer.lineStart = lineStart;
			return token;
		}
		if (code === 92 && body.charCodeAt(position + 1) === 34 && body.charCodeAt(position + 2) === 34 && body.charCodeAt(position + 3) === 34) {
			currentLine += body.slice(chunkStart, position);
			chunkStart = position + 1;
			position += 4;
			continue;
		}
		if (code === 10 || code === 13) {
			currentLine += body.slice(chunkStart, position);
			blockLines.push(currentLine);
			if (code === 13 && body.charCodeAt(position + 1) === 10) position += 2;
			else ++position;
			currentLine = "";
			chunkStart = position;
			lineStart = position;
			continue;
		}
		if (isUnicodeScalarValue(code)) ++position;
		else if (isSupplementaryCodePoint(body, position)) position += 2;
		else throw syntaxError(lexer.source, position, `Invalid character within String: ${printCodePointAt(lexer, position)}.`);
	}
	throw syntaxError(lexer.source, position, "Unterminated string.");
}
/**
* Reads an alphanumeric + underscore name from the source.
*
* ```
* Name ::
*   - NameStart NameContinue* [lookahead != NameContinue]
* ```
*/
function readName(lexer, start) {
	const body = lexer.source.body;
	const bodyLength = body.length;
	let position = start + 1;
	while (position < bodyLength) if (isNameContinue(body.charCodeAt(position))) ++position;
	else break;
	return createToken(lexer, TokenKind.NAME, start, position, body.slice(start, position));
}
//#endregion
//#region node_modules/graphql/jsutils/inspect.mjs
var MAX_ARRAY_LENGTH = 10;
var MAX_RECURSIVE_DEPTH = 2;
/**
* Used to print values in error messages.
*/
function inspect(value) {
	return formatValue(value, []);
}
function formatValue(value, seenValues) {
	switch (typeof value) {
		case "string": return JSON.stringify(value);
		case "function": return value.name ? `[function ${value.name}]` : "[function]";
		case "object": return formatObjectValue(value, seenValues);
		default: return String(value);
	}
}
function formatObjectValue(value, previouslySeenValues) {
	if (value === null) return "null";
	if (previouslySeenValues.includes(value)) return "[Circular]";
	const seenValues = [...previouslySeenValues, value];
	if (isJSONable(value)) {
		const jsonValue = value.toJSON();
		if (jsonValue !== value) return typeof jsonValue === "string" ? jsonValue : formatValue(jsonValue, seenValues);
	} else if (Array.isArray(value)) return formatArray(value, seenValues);
	return formatObject(value, seenValues);
}
function isJSONable(value) {
	return typeof value.toJSON === "function";
}
function formatObject(object, seenValues) {
	const entries = Object.entries(object);
	if (entries.length === 0) return "{}";
	if (seenValues.length > MAX_RECURSIVE_DEPTH) return "[" + getObjectTag(object) + "]";
	return "{ " + entries.map(([key, value]) => key + ": " + formatValue(value, seenValues)).join(", ") + " }";
}
function formatArray(array, seenValues) {
	if (array.length === 0) return "[]";
	if (seenValues.length > MAX_RECURSIVE_DEPTH) return "[Array]";
	const len = Math.min(MAX_ARRAY_LENGTH, array.length);
	const remaining = array.length - len;
	const items = [];
	for (let i = 0; i < len; ++i) items.push(formatValue(array[i], seenValues));
	if (remaining === 1) items.push("... 1 more item");
	else if (remaining > 1) items.push(`... ${remaining} more items`);
	return "[" + items.join(", ") + "]";
}
function getObjectTag(object) {
	const tag = Object.prototype.toString.call(object).replace(/^\[object /, "").replace(/]$/, "");
	if (tag === "Object" && typeof object.constructor === "function") {
		const name = object.constructor.name;
		if (typeof name === "string" && name !== "") return name;
	}
	return tag;
}
/**
* A replacement for instanceof which includes an error warning when multi-realm
* constructors are detected.
* See: https://expressjs.com/en/advanced/best-practice-performance.html#set-node_env-to-production
* See: https://webpack.js.org/guides/production/
*/
var instanceOf = globalThis.process && process.env.NODE_ENV === "production" ? function instanceOf(value, constructor) {
	return value instanceof constructor;
} : function instanceOf(value, constructor) {
	if (value instanceof constructor) return true;
	if (typeof value === "object" && value !== null) {
		var _value$constructor;
		const className = constructor.prototype[Symbol.toStringTag];
		if (className === (Symbol.toStringTag in value ? value[Symbol.toStringTag] : (_value$constructor = value.constructor) === null || _value$constructor === void 0 ? void 0 : _value$constructor.name)) {
			const stringifiedValue = inspect(value);
			throw new Error(`Cannot use ${className} "${stringifiedValue}" from another module or realm.

Ensure that there is only one instance of "graphql" in the node_modules
directory. If different versions of "graphql" are the dependencies of other
relied on modules, use "resolutions" to ensure only one version is installed.

https://yarnpkg.com/en/docs/selective-version-resolutions

Duplicate "graphql" modules cannot be used at the same time since different
versions may have different capabilities and behavior. The data from one
version used in the function from another could produce confusing and
spurious results.`);
		}
	}
	return false;
};
//#endregion
//#region node_modules/graphql/language/source.mjs
/**
* A representation of source input to GraphQL. The `name` and `locationOffset` parameters are
* optional, but they are useful for clients who store GraphQL documents in source files.
* For example, if the GraphQL input starts at line 40 in a file named `Foo.graphql`, it might
* be useful for `name` to be `"Foo.graphql"` and location to be `{ line: 40, column: 1 }`.
* The `line` and `column` properties in `locationOffset` are 1-indexed.
*/
var Source = class {
	constructor(body, name = "GraphQL request", locationOffset = {
		line: 1,
		column: 1
	}) {
		typeof body === "string" || devAssert(false, `Body must be a string. Received: ${inspect(body)}.`);
		this.body = body;
		this.name = name;
		this.locationOffset = locationOffset;
		this.locationOffset.line > 0 || devAssert(false, "line in locationOffset is 1-indexed and must be positive.");
		this.locationOffset.column > 0 || devAssert(false, "column in locationOffset is 1-indexed and must be positive.");
	}
	get [Symbol.toStringTag]() {
		return "Source";
	}
};
/**
* Test if the given value is a Source object.
*
* @internal
*/
function isSource(source) {
	return instanceOf(source, Source);
}
//#endregion
//#region node_modules/graphql/language/parser.mjs
/**
* Configuration options to control parser behavior
*/
/**
* Given a GraphQL source, parses it into a Document.
* Throws GraphQLError if a syntax error is encountered.
*/
function parse(source, options) {
	const parser = new Parser(source, options);
	const document = parser.parseDocument();
	Object.defineProperty(document, "tokenCount", {
		enumerable: false,
		value: parser.tokenCount
	});
	return document;
}
/**
* This class is exported only to assist people in implementing their own parsers
* without duplicating too much code and should be used only as last resort for cases
* such as experimental syntax or if certain features could not be contributed upstream.
*
* It is still part of the internal API and is versioned, so any changes to it are never
* considered breaking changes. If you still need to support multiple versions of the
* library, please use the `versionInfo` variable for version detection.
*
* @internal
*/
var Parser = class {
	constructor(source, options = {}) {
		const sourceObj = isSource(source) ? source : new Source(source);
		this._lexer = new Lexer(sourceObj);
		this._options = options;
		this._tokenCounter = 0;
	}
	get tokenCount() {
		return this._tokenCounter;
	}
	/**
	* Converts a name lex token into a name parse node.
	*/
	parseName() {
		const token = this.expectToken(TokenKind.NAME);
		return this.node(token, {
			kind: Kind.NAME,
			value: token.value
		});
	}
	/**
	* Document : Definition+
	*/
	parseDocument() {
		return this.node(this._lexer.token, {
			kind: Kind.DOCUMENT,
			definitions: this.many(TokenKind.SOF, this.parseDefinition, TokenKind.EOF)
		});
	}
	/**
	* Definition :
	*   - ExecutableDefinition
	*   - TypeSystemDefinition
	*   - TypeSystemExtension
	*
	* ExecutableDefinition :
	*   - OperationDefinition
	*   - FragmentDefinition
	*
	* TypeSystemDefinition :
	*   - SchemaDefinition
	*   - TypeDefinition
	*   - DirectiveDefinition
	*
	* TypeDefinition :
	*   - ScalarTypeDefinition
	*   - ObjectTypeDefinition
	*   - InterfaceTypeDefinition
	*   - UnionTypeDefinition
	*   - EnumTypeDefinition
	*   - InputObjectTypeDefinition
	*/
	parseDefinition() {
		if (this.peek(TokenKind.BRACE_L)) return this.parseOperationDefinition();
		const hasDescription = this.peekDescription();
		const keywordToken = hasDescription ? this._lexer.lookahead() : this._lexer.token;
		if (keywordToken.kind === TokenKind.NAME) {
			switch (keywordToken.value) {
				case "schema": return this.parseSchemaDefinition();
				case "scalar": return this.parseScalarTypeDefinition();
				case "type": return this.parseObjectTypeDefinition();
				case "interface": return this.parseInterfaceTypeDefinition();
				case "union": return this.parseUnionTypeDefinition();
				case "enum": return this.parseEnumTypeDefinition();
				case "input": return this.parseInputObjectTypeDefinition();
				case "directive": return this.parseDirectiveDefinition();
			}
			if (hasDescription) throw syntaxError(this._lexer.source, this._lexer.token.start, "Unexpected description, descriptions are supported only on type definitions.");
			switch (keywordToken.value) {
				case "query":
				case "mutation":
				case "subscription": return this.parseOperationDefinition();
				case "fragment": return this.parseFragmentDefinition();
				case "extend": return this.parseTypeSystemExtension();
			}
		}
		throw this.unexpected(keywordToken);
	}
	/**
	* OperationDefinition :
	*  - SelectionSet
	*  - OperationType Name? VariableDefinitions? Directives? SelectionSet
	*/
	parseOperationDefinition() {
		const start = this._lexer.token;
		if (this.peek(TokenKind.BRACE_L)) return this.node(start, {
			kind: Kind.OPERATION_DEFINITION,
			operation: OperationTypeNode.QUERY,
			name: void 0,
			variableDefinitions: [],
			directives: [],
			selectionSet: this.parseSelectionSet()
		});
		const operation = this.parseOperationType();
		let name;
		if (this.peek(TokenKind.NAME)) name = this.parseName();
		return this.node(start, {
			kind: Kind.OPERATION_DEFINITION,
			operation,
			name,
			variableDefinitions: this.parseVariableDefinitions(),
			directives: this.parseDirectives(false),
			selectionSet: this.parseSelectionSet()
		});
	}
	/**
	* OperationType : one of query mutation subscription
	*/
	parseOperationType() {
		const operationToken = this.expectToken(TokenKind.NAME);
		switch (operationToken.value) {
			case "query": return OperationTypeNode.QUERY;
			case "mutation": return OperationTypeNode.MUTATION;
			case "subscription": return OperationTypeNode.SUBSCRIPTION;
		}
		throw this.unexpected(operationToken);
	}
	/**
	* VariableDefinitions : ( VariableDefinition+ )
	*/
	parseVariableDefinitions() {
		return this.optionalMany(TokenKind.PAREN_L, this.parseVariableDefinition, TokenKind.PAREN_R);
	}
	/**
	* VariableDefinition : Variable : Type DefaultValue? Directives[Const]?
	*/
	parseVariableDefinition() {
		return this.node(this._lexer.token, {
			kind: Kind.VARIABLE_DEFINITION,
			variable: this.parseVariable(),
			type: (this.expectToken(TokenKind.COLON), this.parseTypeReference()),
			defaultValue: this.expectOptionalToken(TokenKind.EQUALS) ? this.parseConstValueLiteral() : void 0,
			directives: this.parseConstDirectives()
		});
	}
	/**
	* Variable : $ Name
	*/
	parseVariable() {
		const start = this._lexer.token;
		this.expectToken(TokenKind.DOLLAR);
		return this.node(start, {
			kind: Kind.VARIABLE,
			name: this.parseName()
		});
	}
	/**
	* ```
	* SelectionSet : { Selection+ }
	* ```
	*/
	parseSelectionSet() {
		return this.node(this._lexer.token, {
			kind: Kind.SELECTION_SET,
			selections: this.many(TokenKind.BRACE_L, this.parseSelection, TokenKind.BRACE_R)
		});
	}
	/**
	* Selection :
	*   - Field
	*   - FragmentSpread
	*   - InlineFragment
	*/
	parseSelection() {
		return this.peek(TokenKind.SPREAD) ? this.parseFragment() : this.parseField();
	}
	/**
	* Field : Alias? Name Arguments? Directives? SelectionSet?
	*
	* Alias : Name :
	*/
	parseField() {
		const start = this._lexer.token;
		const nameOrAlias = this.parseName();
		let alias;
		let name;
		if (this.expectOptionalToken(TokenKind.COLON)) {
			alias = nameOrAlias;
			name = this.parseName();
		} else name = nameOrAlias;
		return this.node(start, {
			kind: Kind.FIELD,
			alias,
			name,
			arguments: this.parseArguments(false),
			directives: this.parseDirectives(false),
			selectionSet: this.peek(TokenKind.BRACE_L) ? this.parseSelectionSet() : void 0
		});
	}
	/**
	* Arguments[Const] : ( Argument[?Const]+ )
	*/
	parseArguments(isConst) {
		const item = isConst ? this.parseConstArgument : this.parseArgument;
		return this.optionalMany(TokenKind.PAREN_L, item, TokenKind.PAREN_R);
	}
	/**
	* Argument[Const] : Name : Value[?Const]
	*/
	parseArgument(isConst = false) {
		const start = this._lexer.token;
		const name = this.parseName();
		this.expectToken(TokenKind.COLON);
		return this.node(start, {
			kind: Kind.ARGUMENT,
			name,
			value: this.parseValueLiteral(isConst)
		});
	}
	parseConstArgument() {
		return this.parseArgument(true);
	}
	/**
	* Corresponds to both FragmentSpread and InlineFragment in the spec.
	*
	* FragmentSpread : ... FragmentName Directives?
	*
	* InlineFragment : ... TypeCondition? Directives? SelectionSet
	*/
	parseFragment() {
		const start = this._lexer.token;
		this.expectToken(TokenKind.SPREAD);
		const hasTypeCondition = this.expectOptionalKeyword("on");
		if (!hasTypeCondition && this.peek(TokenKind.NAME)) return this.node(start, {
			kind: Kind.FRAGMENT_SPREAD,
			name: this.parseFragmentName(),
			directives: this.parseDirectives(false)
		});
		return this.node(start, {
			kind: Kind.INLINE_FRAGMENT,
			typeCondition: hasTypeCondition ? this.parseNamedType() : void 0,
			directives: this.parseDirectives(false),
			selectionSet: this.parseSelectionSet()
		});
	}
	/**
	* FragmentDefinition :
	*   - fragment FragmentName on TypeCondition Directives? SelectionSet
	*
	* TypeCondition : NamedType
	*/
	parseFragmentDefinition() {
		const start = this._lexer.token;
		this.expectKeyword("fragment");
		if (this._options.allowLegacyFragmentVariables === true) return this.node(start, {
			kind: Kind.FRAGMENT_DEFINITION,
			name: this.parseFragmentName(),
			variableDefinitions: this.parseVariableDefinitions(),
			typeCondition: (this.expectKeyword("on"), this.parseNamedType()),
			directives: this.parseDirectives(false),
			selectionSet: this.parseSelectionSet()
		});
		return this.node(start, {
			kind: Kind.FRAGMENT_DEFINITION,
			name: this.parseFragmentName(),
			typeCondition: (this.expectKeyword("on"), this.parseNamedType()),
			directives: this.parseDirectives(false),
			selectionSet: this.parseSelectionSet()
		});
	}
	/**
	* FragmentName : Name but not `on`
	*/
	parseFragmentName() {
		if (this._lexer.token.value === "on") throw this.unexpected();
		return this.parseName();
	}
	/**
	* Value[Const] :
	*   - [~Const] Variable
	*   - IntValue
	*   - FloatValue
	*   - StringValue
	*   - BooleanValue
	*   - NullValue
	*   - EnumValue
	*   - ListValue[?Const]
	*   - ObjectValue[?Const]
	*
	* BooleanValue : one of `true` `false`
	*
	* NullValue : `null`
	*
	* EnumValue : Name but not `true`, `false` or `null`
	*/
	parseValueLiteral(isConst) {
		const token = this._lexer.token;
		switch (token.kind) {
			case TokenKind.BRACKET_L: return this.parseList(isConst);
			case TokenKind.BRACE_L: return this.parseObject(isConst);
			case TokenKind.INT:
				this.advanceLexer();
				return this.node(token, {
					kind: Kind.INT,
					value: token.value
				});
			case TokenKind.FLOAT:
				this.advanceLexer();
				return this.node(token, {
					kind: Kind.FLOAT,
					value: token.value
				});
			case TokenKind.STRING:
			case TokenKind.BLOCK_STRING: return this.parseStringLiteral();
			case TokenKind.NAME:
				this.advanceLexer();
				switch (token.value) {
					case "true": return this.node(token, {
						kind: Kind.BOOLEAN,
						value: true
					});
					case "false": return this.node(token, {
						kind: Kind.BOOLEAN,
						value: false
					});
					case "null": return this.node(token, { kind: Kind.NULL });
					default: return this.node(token, {
						kind: Kind.ENUM,
						value: token.value
					});
				}
			case TokenKind.DOLLAR:
				if (isConst) {
					this.expectToken(TokenKind.DOLLAR);
					if (this._lexer.token.kind === TokenKind.NAME) {
						const varName = this._lexer.token.value;
						throw syntaxError(this._lexer.source, token.start, `Unexpected variable "$${varName}" in constant value.`);
					} else throw this.unexpected(token);
				}
				return this.parseVariable();
			default: throw this.unexpected();
		}
	}
	parseConstValueLiteral() {
		return this.parseValueLiteral(true);
	}
	parseStringLiteral() {
		const token = this._lexer.token;
		this.advanceLexer();
		return this.node(token, {
			kind: Kind.STRING,
			value: token.value,
			block: token.kind === TokenKind.BLOCK_STRING
		});
	}
	/**
	* ListValue[Const] :
	*   - [ ]
	*   - [ Value[?Const]+ ]
	*/
	parseList(isConst) {
		const item = () => this.parseValueLiteral(isConst);
		return this.node(this._lexer.token, {
			kind: Kind.LIST,
			values: this.any(TokenKind.BRACKET_L, item, TokenKind.BRACKET_R)
		});
	}
	/**
	* ```
	* ObjectValue[Const] :
	*   - { }
	*   - { ObjectField[?Const]+ }
	* ```
	*/
	parseObject(isConst) {
		const item = () => this.parseObjectField(isConst);
		return this.node(this._lexer.token, {
			kind: Kind.OBJECT,
			fields: this.any(TokenKind.BRACE_L, item, TokenKind.BRACE_R)
		});
	}
	/**
	* ObjectField[Const] : Name : Value[?Const]
	*/
	parseObjectField(isConst) {
		const start = this._lexer.token;
		const name = this.parseName();
		this.expectToken(TokenKind.COLON);
		return this.node(start, {
			kind: Kind.OBJECT_FIELD,
			name,
			value: this.parseValueLiteral(isConst)
		});
	}
	/**
	* Directives[Const] : Directive[?Const]+
	*/
	parseDirectives(isConst) {
		const directives = [];
		while (this.peek(TokenKind.AT)) directives.push(this.parseDirective(isConst));
		return directives;
	}
	parseConstDirectives() {
		return this.parseDirectives(true);
	}
	/**
	* ```
	* Directive[Const] : @ Name Arguments[?Const]?
	* ```
	*/
	parseDirective(isConst) {
		const start = this._lexer.token;
		this.expectToken(TokenKind.AT);
		return this.node(start, {
			kind: Kind.DIRECTIVE,
			name: this.parseName(),
			arguments: this.parseArguments(isConst)
		});
	}
	/**
	* Type :
	*   - NamedType
	*   - ListType
	*   - NonNullType
	*/
	parseTypeReference() {
		const start = this._lexer.token;
		let type;
		if (this.expectOptionalToken(TokenKind.BRACKET_L)) {
			const innerType = this.parseTypeReference();
			this.expectToken(TokenKind.BRACKET_R);
			type = this.node(start, {
				kind: Kind.LIST_TYPE,
				type: innerType
			});
		} else type = this.parseNamedType();
		if (this.expectOptionalToken(TokenKind.BANG)) return this.node(start, {
			kind: Kind.NON_NULL_TYPE,
			type
		});
		return type;
	}
	/**
	* NamedType : Name
	*/
	parseNamedType() {
		return this.node(this._lexer.token, {
			kind: Kind.NAMED_TYPE,
			name: this.parseName()
		});
	}
	peekDescription() {
		return this.peek(TokenKind.STRING) || this.peek(TokenKind.BLOCK_STRING);
	}
	/**
	* Description : StringValue
	*/
	parseDescription() {
		if (this.peekDescription()) return this.parseStringLiteral();
	}
	/**
	* ```
	* SchemaDefinition : Description? schema Directives[Const]? { OperationTypeDefinition+ }
	* ```
	*/
	parseSchemaDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("schema");
		const directives = this.parseConstDirectives();
		const operationTypes = this.many(TokenKind.BRACE_L, this.parseOperationTypeDefinition, TokenKind.BRACE_R);
		return this.node(start, {
			kind: Kind.SCHEMA_DEFINITION,
			description,
			directives,
			operationTypes
		});
	}
	/**
	* OperationTypeDefinition : OperationType : NamedType
	*/
	parseOperationTypeDefinition() {
		const start = this._lexer.token;
		const operation = this.parseOperationType();
		this.expectToken(TokenKind.COLON);
		const type = this.parseNamedType();
		return this.node(start, {
			kind: Kind.OPERATION_TYPE_DEFINITION,
			operation,
			type
		});
	}
	/**
	* ScalarTypeDefinition : Description? scalar Name Directives[Const]?
	*/
	parseScalarTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("scalar");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		return this.node(start, {
			kind: Kind.SCALAR_TYPE_DEFINITION,
			description,
			name,
			directives
		});
	}
	/**
	* ObjectTypeDefinition :
	*   Description?
	*   type Name ImplementsInterfaces? Directives[Const]? FieldsDefinition?
	*/
	parseObjectTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("type");
		const name = this.parseName();
		const interfaces = this.parseImplementsInterfaces();
		const directives = this.parseConstDirectives();
		const fields = this.parseFieldsDefinition();
		return this.node(start, {
			kind: Kind.OBJECT_TYPE_DEFINITION,
			description,
			name,
			interfaces,
			directives,
			fields
		});
	}
	/**
	* ImplementsInterfaces :
	*   - implements `&`? NamedType
	*   - ImplementsInterfaces & NamedType
	*/
	parseImplementsInterfaces() {
		return this.expectOptionalKeyword("implements") ? this.delimitedMany(TokenKind.AMP, this.parseNamedType) : [];
	}
	/**
	* ```
	* FieldsDefinition : { FieldDefinition+ }
	* ```
	*/
	parseFieldsDefinition() {
		return this.optionalMany(TokenKind.BRACE_L, this.parseFieldDefinition, TokenKind.BRACE_R);
	}
	/**
	* FieldDefinition :
	*   - Description? Name ArgumentsDefinition? : Type Directives[Const]?
	*/
	parseFieldDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		const name = this.parseName();
		const args = this.parseArgumentDefs();
		this.expectToken(TokenKind.COLON);
		const type = this.parseTypeReference();
		const directives = this.parseConstDirectives();
		return this.node(start, {
			kind: Kind.FIELD_DEFINITION,
			description,
			name,
			arguments: args,
			type,
			directives
		});
	}
	/**
	* ArgumentsDefinition : ( InputValueDefinition+ )
	*/
	parseArgumentDefs() {
		return this.optionalMany(TokenKind.PAREN_L, this.parseInputValueDef, TokenKind.PAREN_R);
	}
	/**
	* InputValueDefinition :
	*   - Description? Name : Type DefaultValue? Directives[Const]?
	*/
	parseInputValueDef() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		const name = this.parseName();
		this.expectToken(TokenKind.COLON);
		const type = this.parseTypeReference();
		let defaultValue;
		if (this.expectOptionalToken(TokenKind.EQUALS)) defaultValue = this.parseConstValueLiteral();
		const directives = this.parseConstDirectives();
		return this.node(start, {
			kind: Kind.INPUT_VALUE_DEFINITION,
			description,
			name,
			type,
			defaultValue,
			directives
		});
	}
	/**
	* InterfaceTypeDefinition :
	*   - Description? interface Name Directives[Const]? FieldsDefinition?
	*/
	parseInterfaceTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("interface");
		const name = this.parseName();
		const interfaces = this.parseImplementsInterfaces();
		const directives = this.parseConstDirectives();
		const fields = this.parseFieldsDefinition();
		return this.node(start, {
			kind: Kind.INTERFACE_TYPE_DEFINITION,
			description,
			name,
			interfaces,
			directives,
			fields
		});
	}
	/**
	* UnionTypeDefinition :
	*   - Description? union Name Directives[Const]? UnionMemberTypes?
	*/
	parseUnionTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("union");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const types = this.parseUnionMemberTypes();
		return this.node(start, {
			kind: Kind.UNION_TYPE_DEFINITION,
			description,
			name,
			directives,
			types
		});
	}
	/**
	* UnionMemberTypes :
	*   - = `|`? NamedType
	*   - UnionMemberTypes | NamedType
	*/
	parseUnionMemberTypes() {
		return this.expectOptionalToken(TokenKind.EQUALS) ? this.delimitedMany(TokenKind.PIPE, this.parseNamedType) : [];
	}
	/**
	* EnumTypeDefinition :
	*   - Description? enum Name Directives[Const]? EnumValuesDefinition?
	*/
	parseEnumTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("enum");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const values = this.parseEnumValuesDefinition();
		return this.node(start, {
			kind: Kind.ENUM_TYPE_DEFINITION,
			description,
			name,
			directives,
			values
		});
	}
	/**
	* ```
	* EnumValuesDefinition : { EnumValueDefinition+ }
	* ```
	*/
	parseEnumValuesDefinition() {
		return this.optionalMany(TokenKind.BRACE_L, this.parseEnumValueDefinition, TokenKind.BRACE_R);
	}
	/**
	* EnumValueDefinition : Description? EnumValue Directives[Const]?
	*/
	parseEnumValueDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		const name = this.parseEnumValueName();
		const directives = this.parseConstDirectives();
		return this.node(start, {
			kind: Kind.ENUM_VALUE_DEFINITION,
			description,
			name,
			directives
		});
	}
	/**
	* EnumValue : Name but not `true`, `false` or `null`
	*/
	parseEnumValueName() {
		if (this._lexer.token.value === "true" || this._lexer.token.value === "false" || this._lexer.token.value === "null") throw syntaxError(this._lexer.source, this._lexer.token.start, `${getTokenDesc(this._lexer.token)} is reserved and cannot be used for an enum value.`);
		return this.parseName();
	}
	/**
	* InputObjectTypeDefinition :
	*   - Description? input Name Directives[Const]? InputFieldsDefinition?
	*/
	parseInputObjectTypeDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("input");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const fields = this.parseInputFieldsDefinition();
		return this.node(start, {
			kind: Kind.INPUT_OBJECT_TYPE_DEFINITION,
			description,
			name,
			directives,
			fields
		});
	}
	/**
	* ```
	* InputFieldsDefinition : { InputValueDefinition+ }
	* ```
	*/
	parseInputFieldsDefinition() {
		return this.optionalMany(TokenKind.BRACE_L, this.parseInputValueDef, TokenKind.BRACE_R);
	}
	/**
	* TypeSystemExtension :
	*   - SchemaExtension
	*   - TypeExtension
	*
	* TypeExtension :
	*   - ScalarTypeExtension
	*   - ObjectTypeExtension
	*   - InterfaceTypeExtension
	*   - UnionTypeExtension
	*   - EnumTypeExtension
	*   - InputObjectTypeDefinition
	*/
	parseTypeSystemExtension() {
		const keywordToken = this._lexer.lookahead();
		if (keywordToken.kind === TokenKind.NAME) switch (keywordToken.value) {
			case "schema": return this.parseSchemaExtension();
			case "scalar": return this.parseScalarTypeExtension();
			case "type": return this.parseObjectTypeExtension();
			case "interface": return this.parseInterfaceTypeExtension();
			case "union": return this.parseUnionTypeExtension();
			case "enum": return this.parseEnumTypeExtension();
			case "input": return this.parseInputObjectTypeExtension();
		}
		throw this.unexpected(keywordToken);
	}
	/**
	* ```
	* SchemaExtension :
	*  - extend schema Directives[Const]? { OperationTypeDefinition+ }
	*  - extend schema Directives[Const]
	* ```
	*/
	parseSchemaExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("schema");
		const directives = this.parseConstDirectives();
		const operationTypes = this.optionalMany(TokenKind.BRACE_L, this.parseOperationTypeDefinition, TokenKind.BRACE_R);
		if (directives.length === 0 && operationTypes.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.SCHEMA_EXTENSION,
			directives,
			operationTypes
		});
	}
	/**
	* ScalarTypeExtension :
	*   - extend scalar Name Directives[Const]
	*/
	parseScalarTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("scalar");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		if (directives.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.SCALAR_TYPE_EXTENSION,
			name,
			directives
		});
	}
	/**
	* ObjectTypeExtension :
	*  - extend type Name ImplementsInterfaces? Directives[Const]? FieldsDefinition
	*  - extend type Name ImplementsInterfaces? Directives[Const]
	*  - extend type Name ImplementsInterfaces
	*/
	parseObjectTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("type");
		const name = this.parseName();
		const interfaces = this.parseImplementsInterfaces();
		const directives = this.parseConstDirectives();
		const fields = this.parseFieldsDefinition();
		if (interfaces.length === 0 && directives.length === 0 && fields.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.OBJECT_TYPE_EXTENSION,
			name,
			interfaces,
			directives,
			fields
		});
	}
	/**
	* InterfaceTypeExtension :
	*  - extend interface Name ImplementsInterfaces? Directives[Const]? FieldsDefinition
	*  - extend interface Name ImplementsInterfaces? Directives[Const]
	*  - extend interface Name ImplementsInterfaces
	*/
	parseInterfaceTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("interface");
		const name = this.parseName();
		const interfaces = this.parseImplementsInterfaces();
		const directives = this.parseConstDirectives();
		const fields = this.parseFieldsDefinition();
		if (interfaces.length === 0 && directives.length === 0 && fields.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.INTERFACE_TYPE_EXTENSION,
			name,
			interfaces,
			directives,
			fields
		});
	}
	/**
	* UnionTypeExtension :
	*   - extend union Name Directives[Const]? UnionMemberTypes
	*   - extend union Name Directives[Const]
	*/
	parseUnionTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("union");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const types = this.parseUnionMemberTypes();
		if (directives.length === 0 && types.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.UNION_TYPE_EXTENSION,
			name,
			directives,
			types
		});
	}
	/**
	* EnumTypeExtension :
	*   - extend enum Name Directives[Const]? EnumValuesDefinition
	*   - extend enum Name Directives[Const]
	*/
	parseEnumTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("enum");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const values = this.parseEnumValuesDefinition();
		if (directives.length === 0 && values.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.ENUM_TYPE_EXTENSION,
			name,
			directives,
			values
		});
	}
	/**
	* InputObjectTypeExtension :
	*   - extend input Name Directives[Const]? InputFieldsDefinition
	*   - extend input Name Directives[Const]
	*/
	parseInputObjectTypeExtension() {
		const start = this._lexer.token;
		this.expectKeyword("extend");
		this.expectKeyword("input");
		const name = this.parseName();
		const directives = this.parseConstDirectives();
		const fields = this.parseInputFieldsDefinition();
		if (directives.length === 0 && fields.length === 0) throw this.unexpected();
		return this.node(start, {
			kind: Kind.INPUT_OBJECT_TYPE_EXTENSION,
			name,
			directives,
			fields
		});
	}
	/**
	* ```
	* DirectiveDefinition :
	*   - Description? directive @ Name ArgumentsDefinition? `repeatable`? on DirectiveLocations
	* ```
	*/
	parseDirectiveDefinition() {
		const start = this._lexer.token;
		const description = this.parseDescription();
		this.expectKeyword("directive");
		this.expectToken(TokenKind.AT);
		const name = this.parseName();
		const args = this.parseArgumentDefs();
		const repeatable = this.expectOptionalKeyword("repeatable");
		this.expectKeyword("on");
		const locations = this.parseDirectiveLocations();
		return this.node(start, {
			kind: Kind.DIRECTIVE_DEFINITION,
			description,
			name,
			arguments: args,
			repeatable,
			locations
		});
	}
	/**
	* DirectiveLocations :
	*   - `|`? DirectiveLocation
	*   - DirectiveLocations | DirectiveLocation
	*/
	parseDirectiveLocations() {
		return this.delimitedMany(TokenKind.PIPE, this.parseDirectiveLocation);
	}
	parseDirectiveLocation() {
		const start = this._lexer.token;
		const name = this.parseName();
		if (Object.prototype.hasOwnProperty.call(DirectiveLocation, name.value)) return name;
		throw this.unexpected(start);
	}
	/**
	* Returns a node that, if configured to do so, sets a "loc" field as a
	* location object, used to identify the place in the source that created a
	* given parsed object.
	*/
	node(startToken, node) {
		if (this._options.noLocation !== true) node.loc = new Location(startToken, this._lexer.lastToken, this._lexer.source);
		return node;
	}
	/**
	* Determines if the next token is of a given kind
	*/
	peek(kind) {
		return this._lexer.token.kind === kind;
	}
	/**
	* If the next token is of the given kind, return that token after advancing the lexer.
	* Otherwise, do not change the parser state and throw an error.
	*/
	expectToken(kind) {
		const token = this._lexer.token;
		if (token.kind === kind) {
			this.advanceLexer();
			return token;
		}
		throw syntaxError(this._lexer.source, token.start, `Expected ${getTokenKindDesc(kind)}, found ${getTokenDesc(token)}.`);
	}
	/**
	* If the next token is of the given kind, return "true" after advancing the lexer.
	* Otherwise, do not change the parser state and return "false".
	*/
	expectOptionalToken(kind) {
		if (this._lexer.token.kind === kind) {
			this.advanceLexer();
			return true;
		}
		return false;
	}
	/**
	* If the next token is a given keyword, advance the lexer.
	* Otherwise, do not change the parser state and throw an error.
	*/
	expectKeyword(value) {
		const token = this._lexer.token;
		if (token.kind === TokenKind.NAME && token.value === value) this.advanceLexer();
		else throw syntaxError(this._lexer.source, token.start, `Expected "${value}", found ${getTokenDesc(token)}.`);
	}
	/**
	* If the next token is a given keyword, return "true" after advancing the lexer.
	* Otherwise, do not change the parser state and return "false".
	*/
	expectOptionalKeyword(value) {
		const token = this._lexer.token;
		if (token.kind === TokenKind.NAME && token.value === value) {
			this.advanceLexer();
			return true;
		}
		return false;
	}
	/**
	* Helper function for creating an error when an unexpected lexed token is encountered.
	*/
	unexpected(atToken) {
		const token = atToken !== null && atToken !== void 0 ? atToken : this._lexer.token;
		return syntaxError(this._lexer.source, token.start, `Unexpected ${getTokenDesc(token)}.`);
	}
	/**
	* Returns a possibly empty list of parse nodes, determined by the parseFn.
	* This list begins with a lex token of openKind and ends with a lex token of closeKind.
	* Advances the parser to the next lex token after the closing token.
	*/
	any(openKind, parseFn, closeKind) {
		this.expectToken(openKind);
		const nodes = [];
		while (!this.expectOptionalToken(closeKind)) nodes.push(parseFn.call(this));
		return nodes;
	}
	/**
	* Returns a list of parse nodes, determined by the parseFn.
	* It can be empty only if open token is missing otherwise it will always return non-empty list
	* that begins with a lex token of openKind and ends with a lex token of closeKind.
	* Advances the parser to the next lex token after the closing token.
	*/
	optionalMany(openKind, parseFn, closeKind) {
		if (this.expectOptionalToken(openKind)) {
			const nodes = [];
			do
				nodes.push(parseFn.call(this));
			while (!this.expectOptionalToken(closeKind));
			return nodes;
		}
		return [];
	}
	/**
	* Returns a non-empty list of parse nodes, determined by the parseFn.
	* This list begins with a lex token of openKind and ends with a lex token of closeKind.
	* Advances the parser to the next lex token after the closing token.
	*/
	many(openKind, parseFn, closeKind) {
		this.expectToken(openKind);
		const nodes = [];
		do
			nodes.push(parseFn.call(this));
		while (!this.expectOptionalToken(closeKind));
		return nodes;
	}
	/**
	* Returns a non-empty list of parse nodes, determined by the parseFn.
	* This list may begin with a lex token of delimiterKind followed by items separated by lex tokens of tokenKind.
	* Advances the parser to the next lex token after last item in the list.
	*/
	delimitedMany(delimiterKind, parseFn) {
		this.expectOptionalToken(delimiterKind);
		const nodes = [];
		do
			nodes.push(parseFn.call(this));
		while (this.expectOptionalToken(delimiterKind));
		return nodes;
	}
	advanceLexer() {
		const { maxTokens } = this._options;
		const token = this._lexer.advance();
		if (token.kind !== TokenKind.EOF) {
			++this._tokenCounter;
			if (maxTokens !== void 0 && this._tokenCounter > maxTokens) throw syntaxError(this._lexer.source, token.start, `Document contains more that ${maxTokens} tokens. Parsing aborted.`);
		}
	}
};
/**
* A helper function to describe a token as a string for debugging.
*/
function getTokenDesc(token) {
	const value = token.value;
	return getTokenKindDesc(token.kind) + (value != null ? ` "${value}"` : "");
}
/**
* A helper function to describe a token kind as a string for debugging.
*/
function getTokenKindDesc(kind) {
	return isPunctuatorTokenKind(kind) ? `"${kind}"` : kind;
}
//#endregion
//#region node_modules/graphql/language/printString.mjs
/**
* Prints a string as a GraphQL StringValue literal. Replaces control characters
* and excluded characters (" U+0022 and \\ U+005C) with escape sequences.
*/
function printString(str) {
	return `"${str.replace(escapedRegExp, escapedReplacer)}"`;
}
var escapedRegExp = /[\x00-\x1f\x22\x5c\x7f-\x9f]/g;
function escapedReplacer(str) {
	return escapeSequences[str.charCodeAt(0)];
}
var escapeSequences = [
	"\\u0000",
	"\\u0001",
	"\\u0002",
	"\\u0003",
	"\\u0004",
	"\\u0005",
	"\\u0006",
	"\\u0007",
	"\\b",
	"\\t",
	"\\n",
	"\\u000B",
	"\\f",
	"\\r",
	"\\u000E",
	"\\u000F",
	"\\u0010",
	"\\u0011",
	"\\u0012",
	"\\u0013",
	"\\u0014",
	"\\u0015",
	"\\u0016",
	"\\u0017",
	"\\u0018",
	"\\u0019",
	"\\u001A",
	"\\u001B",
	"\\u001C",
	"\\u001D",
	"\\u001E",
	"\\u001F",
	"",
	"",
	"\\\"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"\\\\",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"",
	"\\u007F",
	"\\u0080",
	"\\u0081",
	"\\u0082",
	"\\u0083",
	"\\u0084",
	"\\u0085",
	"\\u0086",
	"\\u0087",
	"\\u0088",
	"\\u0089",
	"\\u008A",
	"\\u008B",
	"\\u008C",
	"\\u008D",
	"\\u008E",
	"\\u008F",
	"\\u0090",
	"\\u0091",
	"\\u0092",
	"\\u0093",
	"\\u0094",
	"\\u0095",
	"\\u0096",
	"\\u0097",
	"\\u0098",
	"\\u0099",
	"\\u009A",
	"\\u009B",
	"\\u009C",
	"\\u009D",
	"\\u009E",
	"\\u009F"
];
//#endregion
//#region node_modules/graphql/language/visitor.mjs
/**
* A visitor is provided to visit, it contains the collection of
* relevant functions to be called during the visitor's traversal.
*/
var BREAK = Object.freeze({});
/**
* visit() will walk through an AST using a depth-first traversal, calling
* the visitor's enter function at each node in the traversal, and calling the
* leave function after visiting that node and all of its child nodes.
*
* By returning different values from the enter and leave functions, the
* behavior of the visitor can be altered, including skipping over a sub-tree of
* the AST (by returning false), editing the AST by returning a value or null
* to remove the value, or to stop the whole traversal by returning BREAK.
*
* When using visit() to edit an AST, the original AST will not be modified, and
* a new version of the AST with the changes applied will be returned from the
* visit function.
*
* ```ts
* const editedAST = visit(ast, {
*   enter(node, key, parent, path, ancestors) {
*     // @return
*     //   undefined: no action
*     //   false: skip visiting this node
*     //   visitor.BREAK: stop visiting altogether
*     //   null: delete this node
*     //   any value: replace this node with the returned value
*   },
*   leave(node, key, parent, path, ancestors) {
*     // @return
*     //   undefined: no action
*     //   false: no action
*     //   visitor.BREAK: stop visiting altogether
*     //   null: delete this node
*     //   any value: replace this node with the returned value
*   }
* });
* ```
*
* Alternatively to providing enter() and leave() functions, a visitor can
* instead provide functions named the same as the kinds of AST nodes, or
* enter/leave visitors at a named key, leading to three permutations of the
* visitor API:
*
* 1) Named visitors triggered when entering a node of a specific kind.
*
* ```ts
* visit(ast, {
*   Kind(node) {
*     // enter the "Kind" node
*   }
* })
* ```
*
* 2) Named visitors that trigger upon entering and leaving a node of a specific kind.
*
* ```ts
* visit(ast, {
*   Kind: {
*     enter(node) {
*       // enter the "Kind" node
*     }
*     leave(node) {
*       // leave the "Kind" node
*     }
*   }
* })
* ```
*
* 3) Generic visitors that trigger upon entering and leaving any node.
*
* ```ts
* visit(ast, {
*   enter(node) {
*     // enter any node
*   },
*   leave(node) {
*     // leave any node
*   }
* })
* ```
*/
function visit(root, visitor, visitorKeys = QueryDocumentKeys) {
	const enterLeaveMap = /* @__PURE__ */ new Map();
	for (const kind of Object.values(Kind)) enterLeaveMap.set(kind, getEnterLeaveForKind(visitor, kind));
	let stack = void 0;
	let inArray = Array.isArray(root);
	let keys = [root];
	let index = -1;
	let edits = [];
	let node = root;
	let key = void 0;
	let parent = void 0;
	const path = [];
	const ancestors = [];
	do {
		index++;
		const isLeaving = index === keys.length;
		const isEdited = isLeaving && edits.length !== 0;
		if (isLeaving) {
			key = ancestors.length === 0 ? void 0 : path[path.length - 1];
			node = parent;
			parent = ancestors.pop();
			if (isEdited) if (inArray) {
				node = node.slice();
				let editOffset = 0;
				for (const [editKey, editValue] of edits) {
					const arrayKey = editKey - editOffset;
					if (editValue === null) {
						node.splice(arrayKey, 1);
						editOffset++;
					} else node[arrayKey] = editValue;
				}
			} else {
				node = { ...node };
				for (const [editKey, editValue] of edits) node[editKey] = editValue;
			}
			index = stack.index;
			keys = stack.keys;
			edits = stack.edits;
			inArray = stack.inArray;
			stack = stack.prev;
		} else if (parent) {
			key = inArray ? index : keys[index];
			node = parent[key];
			if (node === null || node === void 0) continue;
			path.push(key);
		}
		let result;
		if (!Array.isArray(node)) {
			var _enterLeaveMap$get, _enterLeaveMap$get2;
			isNode(node) || devAssert(false, `Invalid AST Node: ${inspect(node)}.`);
			const visitFn = isLeaving ? (_enterLeaveMap$get = enterLeaveMap.get(node.kind)) === null || _enterLeaveMap$get === void 0 ? void 0 : _enterLeaveMap$get.leave : (_enterLeaveMap$get2 = enterLeaveMap.get(node.kind)) === null || _enterLeaveMap$get2 === void 0 ? void 0 : _enterLeaveMap$get2.enter;
			result = visitFn === null || visitFn === void 0 ? void 0 : visitFn.call(visitor, node, key, parent, path, ancestors);
			if (result === BREAK) break;
			if (result === false) {
				if (!isLeaving) {
					path.pop();
					continue;
				}
			} else if (result !== void 0) {
				edits.push([key, result]);
				if (!isLeaving) if (isNode(result)) node = result;
				else {
					path.pop();
					continue;
				}
			}
		}
		if (result === void 0 && isEdited) edits.push([key, node]);
		if (isLeaving) path.pop();
		else {
			var _node$kind;
			stack = {
				inArray,
				index,
				keys,
				edits,
				prev: stack
			};
			inArray = Array.isArray(node);
			keys = inArray ? node : (_node$kind = visitorKeys[node.kind]) !== null && _node$kind !== void 0 ? _node$kind : [];
			index = -1;
			edits = [];
			if (parent) ancestors.push(parent);
			parent = node;
		}
	} while (stack !== void 0);
	if (edits.length !== 0) return edits[edits.length - 1][1];
	return root;
}
/**
* Given a visitor instance and a node kind, return EnterLeaveVisitor for that kind.
*/
function getEnterLeaveForKind(visitor, kind) {
	const kindVisitor = visitor[kind];
	if (typeof kindVisitor === "object") return kindVisitor;
	else if (typeof kindVisitor === "function") return {
		enter: kindVisitor,
		leave: void 0
	};
	return {
		enter: visitor.enter,
		leave: visitor.leave
	};
}
//#endregion
//#region node_modules/graphql/language/printer.mjs
/**
* Converts an AST into a string, using one set of reasonable
* formatting rules.
*/
function print$1(ast) {
	return visit(ast, printDocASTReducer);
}
var MAX_LINE_LENGTH = 80;
var printDocASTReducer = {
	Name: { leave: (node) => node.value },
	Variable: { leave: (node) => "$" + node.name },
	Document: { leave: (node) => join(node.definitions, "\n\n") },
	OperationDefinition: { leave(node) {
		const varDefs = wrap$1("(", join(node.variableDefinitions, ", "), ")");
		const prefix = join([
			node.operation,
			join([node.name, varDefs]),
			join(node.directives, " ")
		], " ");
		return (prefix === "query" ? "" : prefix + " ") + node.selectionSet;
	} },
	VariableDefinition: { leave: ({ variable, type, defaultValue, directives }) => variable + ": " + type + wrap$1(" = ", defaultValue) + wrap$1(" ", join(directives, " ")) },
	SelectionSet: { leave: ({ selections }) => block(selections) },
	Field: { leave({ alias, name, arguments: args, directives, selectionSet }) {
		const prefix = wrap$1("", alias, ": ") + name;
		let argsLine = prefix + wrap$1("(", join(args, ", "), ")");
		if (argsLine.length > MAX_LINE_LENGTH) argsLine = prefix + wrap$1("(\n", indent(join(args, "\n")), "\n)");
		return join([
			argsLine,
			join(directives, " "),
			selectionSet
		], " ");
	} },
	Argument: { leave: ({ name, value }) => name + ": " + value },
	FragmentSpread: { leave: ({ name, directives }) => "..." + name + wrap$1(" ", join(directives, " ")) },
	InlineFragment: { leave: ({ typeCondition, directives, selectionSet }) => join([
		"...",
		wrap$1("on ", typeCondition),
		join(directives, " "),
		selectionSet
	], " ") },
	FragmentDefinition: { leave: ({ name, typeCondition, variableDefinitions, directives, selectionSet }) => `fragment ${name}${wrap$1("(", join(variableDefinitions, ", "), ")")} on ${typeCondition} ${wrap$1("", join(directives, " "), " ")}` + selectionSet },
	IntValue: { leave: ({ value }) => value },
	FloatValue: { leave: ({ value }) => value },
	StringValue: { leave: ({ value, block: isBlockString }) => isBlockString ? printBlockString(value) : printString(value) },
	BooleanValue: { leave: ({ value }) => value ? "true" : "false" },
	NullValue: { leave: () => "null" },
	EnumValue: { leave: ({ value }) => value },
	ListValue: { leave: ({ values }) => "[" + join(values, ", ") + "]" },
	ObjectValue: { leave: ({ fields }) => "{" + join(fields, ", ") + "}" },
	ObjectField: { leave: ({ name, value }) => name + ": " + value },
	Directive: { leave: ({ name, arguments: args }) => "@" + name + wrap$1("(", join(args, ", "), ")") },
	NamedType: { leave: ({ name }) => name },
	ListType: { leave: ({ type }) => "[" + type + "]" },
	NonNullType: { leave: ({ type }) => type + "!" },
	SchemaDefinition: { leave: ({ description, directives, operationTypes }) => wrap$1("", description, "\n") + join([
		"schema",
		join(directives, " "),
		block(operationTypes)
	], " ") },
	OperationTypeDefinition: { leave: ({ operation, type }) => operation + ": " + type },
	ScalarTypeDefinition: { leave: ({ description, name, directives }) => wrap$1("", description, "\n") + join([
		"scalar",
		name,
		join(directives, " ")
	], " ") },
	ObjectTypeDefinition: { leave: ({ description, name, interfaces, directives, fields }) => wrap$1("", description, "\n") + join([
		"type",
		name,
		wrap$1("implements ", join(interfaces, " & ")),
		join(directives, " "),
		block(fields)
	], " ") },
	FieldDefinition: { leave: ({ description, name, arguments: args, type, directives }) => wrap$1("", description, "\n") + name + (hasMultilineItems(args) ? wrap$1("(\n", indent(join(args, "\n")), "\n)") : wrap$1("(", join(args, ", "), ")")) + ": " + type + wrap$1(" ", join(directives, " ")) },
	InputValueDefinition: { leave: ({ description, name, type, defaultValue, directives }) => wrap$1("", description, "\n") + join([
		name + ": " + type,
		wrap$1("= ", defaultValue),
		join(directives, " ")
	], " ") },
	InterfaceTypeDefinition: { leave: ({ description, name, interfaces, directives, fields }) => wrap$1("", description, "\n") + join([
		"interface",
		name,
		wrap$1("implements ", join(interfaces, " & ")),
		join(directives, " "),
		block(fields)
	], " ") },
	UnionTypeDefinition: { leave: ({ description, name, directives, types }) => wrap$1("", description, "\n") + join([
		"union",
		name,
		join(directives, " "),
		wrap$1("= ", join(types, " | "))
	], " ") },
	EnumTypeDefinition: { leave: ({ description, name, directives, values }) => wrap$1("", description, "\n") + join([
		"enum",
		name,
		join(directives, " "),
		block(values)
	], " ") },
	EnumValueDefinition: { leave: ({ description, name, directives }) => wrap$1("", description, "\n") + join([name, join(directives, " ")], " ") },
	InputObjectTypeDefinition: { leave: ({ description, name, directives, fields }) => wrap$1("", description, "\n") + join([
		"input",
		name,
		join(directives, " "),
		block(fields)
	], " ") },
	DirectiveDefinition: { leave: ({ description, name, arguments: args, repeatable, locations }) => wrap$1("", description, "\n") + "directive @" + name + (hasMultilineItems(args) ? wrap$1("(\n", indent(join(args, "\n")), "\n)") : wrap$1("(", join(args, ", "), ")")) + (repeatable ? " repeatable" : "") + " on " + join(locations, " | ") },
	SchemaExtension: { leave: ({ directives, operationTypes }) => join([
		"extend schema",
		join(directives, " "),
		block(operationTypes)
	], " ") },
	ScalarTypeExtension: { leave: ({ name, directives }) => join([
		"extend scalar",
		name,
		join(directives, " ")
	], " ") },
	ObjectTypeExtension: { leave: ({ name, interfaces, directives, fields }) => join([
		"extend type",
		name,
		wrap$1("implements ", join(interfaces, " & ")),
		join(directives, " "),
		block(fields)
	], " ") },
	InterfaceTypeExtension: { leave: ({ name, interfaces, directives, fields }) => join([
		"extend interface",
		name,
		wrap$1("implements ", join(interfaces, " & ")),
		join(directives, " "),
		block(fields)
	], " ") },
	UnionTypeExtension: { leave: ({ name, directives, types }) => join([
		"extend union",
		name,
		join(directives, " "),
		wrap$1("= ", join(types, " | "))
	], " ") },
	EnumTypeExtension: { leave: ({ name, directives, values }) => join([
		"extend enum",
		name,
		join(directives, " "),
		block(values)
	], " ") },
	InputObjectTypeExtension: { leave: ({ name, directives, fields }) => join([
		"extend input",
		name,
		join(directives, " "),
		block(fields)
	], " ") }
};
/**
* Given maybeArray, print an empty string if it is null or empty, otherwise
* print all items together separated by separator if provided
*/
function join(maybeArray, separator = "") {
	var _maybeArray$filter$jo;
	return (_maybeArray$filter$jo = maybeArray === null || maybeArray === void 0 ? void 0 : maybeArray.filter((x) => x).join(separator)) !== null && _maybeArray$filter$jo !== void 0 ? _maybeArray$filter$jo : "";
}
/**
* Given array, print each item on its own line, wrapped in an indented `{ }` block.
*/
function block(array) {
	return wrap$1("{\n", indent(join(array, "\n")), "\n}");
}
/**
* If maybeString is not null or empty, then wrap with start and end, otherwise print an empty string.
*/
function wrap$1(start, maybeString, end = "") {
	return maybeString != null && maybeString !== "" ? start + maybeString + end : "";
}
function indent(str) {
	return wrap$1("  ", str.replace(/\n/g, "\n  "));
}
function hasMultilineItems(maybeArray) {
	var _maybeArray$some;
	/* c8 ignore next */
	return (_maybeArray$some = maybeArray === null || maybeArray === void 0 ? void 0 : maybeArray.some((str) => str.includes("\n"))) !== null && _maybeArray$some !== void 0 ? _maybeArray$some : false;
}
//#endregion
//#region node_modules/graphql/language/predicates.mjs
function isSelectionNode(node) {
	return node.kind === Kind.FIELD || node.kind === Kind.FRAGMENT_SPREAD || node.kind === Kind.INLINE_FRAGMENT;
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/directives.js
function shouldInclude(_a, variables) {
	var directives = _a.directives;
	if (!directives || !directives.length) return true;
	return getInclusionDirectives(directives).every(function(_a) {
		var directive = _a.directive, ifArgument = _a.ifArgument;
		var evaledValue = false;
		if (ifArgument.value.kind === "Variable") {
			evaledValue = variables && variables[ifArgument.value.name.value];
			invariant$1(evaledValue !== void 0, 106, directive.name.value);
		} else evaledValue = ifArgument.value.value;
		return directive.name.value === "skip" ? !evaledValue : evaledValue;
	});
}
function hasDirectives(names, root, all) {
	var nameSet = new Set(names);
	var uniqueCount = nameSet.size;
	visit(root, { Directive: function(node) {
		if (nameSet.delete(node.name.value) && (!all || !nameSet.size)) return BREAK;
	} });
	return all ? !nameSet.size : nameSet.size < uniqueCount;
}
function hasClientExports(document) {
	return document && hasDirectives(["client", "export"], document, true);
}
function isInclusionDirective(_a) {
	var value = _a.name.value;
	return value === "skip" || value === "include";
}
function getInclusionDirectives(directives) {
	var result = [];
	if (directives && directives.length) directives.forEach(function(directive) {
		if (!isInclusionDirective(directive)) return;
		var directiveArguments = directive.arguments;
		var directiveName = directive.name.value;
		invariant$1(directiveArguments && directiveArguments.length === 1, 107, directiveName);
		var ifArgument = directiveArguments[0];
		invariant$1(ifArgument.name && ifArgument.name.value === "if", 108, directiveName);
		var ifValue = ifArgument.value;
		invariant$1(ifValue && (ifValue.kind === "Variable" || ifValue.kind === "BooleanValue"), 109, directiveName);
		result.push({
			directive,
			ifArgument
		});
	});
	return result;
}
/** @internal */
function getFragmentMaskMode(fragment) {
	var _a, _b;
	var directive = (_a = fragment.directives) === null || _a === void 0 ? void 0 : _a.find(function(_a) {
		return _a.name.value === "unmask";
	});
	if (!directive) return "mask";
	var modeArg = (_b = directive.arguments) === null || _b === void 0 ? void 0 : _b.find(function(_a) {
		return _a.name.value === "mode";
	});
	if (globalThis.__DEV__ !== false) {
		if (modeArg) {
			if (modeArg.value.kind === Kind.VARIABLE) globalThis.__DEV__ !== false && invariant$1.warn(110);
			else if (modeArg.value.kind !== Kind.STRING) globalThis.__DEV__ !== false && invariant$1.warn(111);
			else if (modeArg.value.value !== "migrate") globalThis.__DEV__ !== false && invariant$1.warn(112, modeArg.value.value);
		}
	}
	if (modeArg && "value" in modeArg.value && modeArg.value.value === "migrate") return "migrate";
	return "unmask";
}
//#endregion
//#region node_modules/@wry/trie/lib/index.js
var defaultMakeData = () => Object.create(null);
var { forEach, slice } = Array.prototype;
var { hasOwnProperty: hasOwnProperty$6 } = Object.prototype;
var Trie = class Trie {
	constructor(weakness = true, makeData = defaultMakeData) {
		this.weakness = weakness;
		this.makeData = makeData;
	}
	lookup() {
		return this.lookupArray(arguments);
	}
	lookupArray(array) {
		let node = this;
		forEach.call(array, (key) => node = node.getChildTrie(key));
		return hasOwnProperty$6.call(node, "data") ? node.data : node.data = this.makeData(slice.call(array));
	}
	peek() {
		return this.peekArray(arguments);
	}
	peekArray(array) {
		let node = this;
		for (let i = 0, len = array.length; node && i < len; ++i) {
			const map = node.mapFor(array[i], false);
			node = map && map.get(array[i]);
		}
		return node && node.data;
	}
	remove() {
		return this.removeArray(arguments);
	}
	removeArray(array) {
		let data;
		if (array.length) {
			const head = array[0];
			const map = this.mapFor(head, false);
			const child = map && map.get(head);
			if (child) {
				data = child.removeArray(slice.call(array, 1));
				if (!child.data && !child.weak && !(child.strong && child.strong.size)) map.delete(head);
			}
		} else {
			data = this.data;
			delete this.data;
		}
		return data;
	}
	getChildTrie(key) {
		const map = this.mapFor(key, true);
		let child = map.get(key);
		if (!child) map.set(key, child = new Trie(this.weakness, this.makeData));
		return child;
	}
	mapFor(key, create) {
		return this.weakness && isObjRef(key) ? this.weak || (create ? this.weak = /* @__PURE__ */ new WeakMap() : void 0) : this.strong || (create ? this.strong = /* @__PURE__ */ new Map() : void 0);
	}
};
function isObjRef(value) {
	switch (typeof value) {
		case "object": if (value === null) break;
		case "function": return true;
	}
	return false;
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/canUse.js
var isReactNative = maybe$1(function() {
	return navigator.product;
}) == "ReactNative";
var canUseWeakMap = typeof WeakMap === "function" && !(isReactNative && !global.HermesInternal);
var canUseWeakSet = typeof WeakSet === "function";
var canUseSymbol = typeof Symbol === "function" && typeof Symbol.for === "function";
var canUseAsyncIteratorSymbol = canUseSymbol && Symbol.asyncIterator;
maybe$1(function() {
	return window.document.createElement;
});
maybe$1(function() {
	return navigator.userAgent.indexOf("jsdom") >= 0;
});
//#endregion
//#region node_modules/@apollo/client/utilities/common/objects.js
function isNonNullObject(obj) {
	return obj !== null && typeof obj === "object";
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/fragments.js
/**
* Returns a query document which adds a single query operation that only
* spreads the target fragment inside of it.
*
* So for example a document of:
*
* ```graphql
* fragment foo on Foo { a b c }
* ```
*
* Turns into:
*
* ```graphql
* { ...foo }
*
* fragment foo on Foo { a b c }
* ```
*
* The target fragment will either be the only fragment in the document, or a
* fragment specified by the provided `fragmentName`. If there is more than one
* fragment, but a `fragmentName` was not defined then an error will be thrown.
*/
function getFragmentQueryDocument(document, fragmentName) {
	var actualFragmentName = fragmentName;
	var fragments = [];
	document.definitions.forEach(function(definition) {
		if (definition.kind === "OperationDefinition") throw newInvariantError(113, definition.operation, definition.name ? " named '".concat(definition.name.value, "'") : "");
		if (definition.kind === "FragmentDefinition") fragments.push(definition);
	});
	if (typeof actualFragmentName === "undefined") {
		invariant$1(fragments.length === 1, 114, fragments.length);
		actualFragmentName = fragments[0].name.value;
	}
	return __assign(__assign({}, document), { definitions: __spreadArray([{
		kind: "OperationDefinition",
		operation: "query",
		selectionSet: {
			kind: "SelectionSet",
			selections: [{
				kind: "FragmentSpread",
				name: {
					kind: "Name",
					value: actualFragmentName
				}
			}]
		}
	}], document.definitions, true) });
}
function createFragmentMap(fragments) {
	if (fragments === void 0) fragments = [];
	var symTable = {};
	fragments.forEach(function(fragment) {
		symTable[fragment.name.value] = fragment;
	});
	return symTable;
}
function getFragmentFromSelection(selection, fragmentMap) {
	switch (selection.kind) {
		case "InlineFragment": return selection;
		case "FragmentSpread":
			var fragmentName = selection.name.value;
			if (typeof fragmentMap === "function") return fragmentMap(fragmentName);
			var fragment = fragmentMap && fragmentMap[fragmentName];
			invariant$1(fragment, 115, fragmentName);
			return fragment || null;
		default: return null;
	}
}
function isFullyUnmaskedOperation(document) {
	var isUnmasked = true;
	visit(document, { FragmentSpread: function(node) {
		isUnmasked = !!node.directives && node.directives.some(function(directive) {
			return directive.name.value === "unmask";
		});
		if (!isUnmasked) return BREAK;
	} });
	return isUnmasked;
}
//#endregion
//#region node_modules/@wry/caches/lib/strong.js
function defaultDispose$1() {}
var StrongCache = class {
	constructor(max = Infinity, dispose = defaultDispose$1) {
		this.max = max;
		this.dispose = dispose;
		this.map = /* @__PURE__ */ new Map();
		this.newest = null;
		this.oldest = null;
	}
	has(key) {
		return this.map.has(key);
	}
	get(key) {
		const node = this.getNode(key);
		return node && node.value;
	}
	get size() {
		return this.map.size;
	}
	getNode(key) {
		const node = this.map.get(key);
		if (node && node !== this.newest) {
			const { older, newer } = node;
			if (newer) newer.older = older;
			if (older) older.newer = newer;
			node.older = this.newest;
			node.older.newer = node;
			node.newer = null;
			this.newest = node;
			if (node === this.oldest) this.oldest = newer;
		}
		return node;
	}
	set(key, value) {
		let node = this.getNode(key);
		if (node) return node.value = value;
		node = {
			key,
			value,
			newer: null,
			older: this.newest
		};
		if (this.newest) this.newest.newer = node;
		this.newest = node;
		this.oldest = this.oldest || node;
		this.map.set(key, node);
		return node.value;
	}
	clean() {
		while (this.oldest && this.map.size > this.max) this.delete(this.oldest.key);
	}
	delete(key) {
		const node = this.map.get(key);
		if (node) {
			if (node === this.newest) this.newest = node.older;
			if (node === this.oldest) this.oldest = node.newer;
			if (node.newer) node.newer.older = node.older;
			if (node.older) node.older.newer = node.newer;
			this.map.delete(key);
			this.dispose(node.value, key);
			return true;
		}
		return false;
	}
};
//#endregion
//#region node_modules/@wry/caches/lib/weak.js
function noop() {}
var defaultDispose = noop;
var _WeakRef = typeof WeakRef !== "undefined" ? WeakRef : function(value) {
	return { deref: () => value };
};
var _WeakMap = typeof WeakMap !== "undefined" ? WeakMap : Map;
var _FinalizationRegistry = typeof FinalizationRegistry !== "undefined" ? FinalizationRegistry : function() {
	return {
		register: noop,
		unregister: noop
	};
};
var finalizationBatchSize = 10024;
var WeakCache = class {
	constructor(max = Infinity, dispose = defaultDispose) {
		this.max = max;
		this.dispose = dispose;
		this.map = new _WeakMap();
		this.newest = null;
		this.oldest = null;
		this.unfinalizedNodes = /* @__PURE__ */ new Set();
		this.finalizationScheduled = false;
		this.size = 0;
		this.finalize = () => {
			const iterator = this.unfinalizedNodes.values();
			for (let i = 0; i < finalizationBatchSize; i++) {
				const node = iterator.next().value;
				if (!node) break;
				this.unfinalizedNodes.delete(node);
				const key = node.key;
				delete node.key;
				node.keyRef = new _WeakRef(key);
				this.registry.register(key, node, node);
			}
			if (this.unfinalizedNodes.size > 0) queueMicrotask(this.finalize);
			else this.finalizationScheduled = false;
		};
		this.registry = new _FinalizationRegistry(this.deleteNode.bind(this));
	}
	has(key) {
		return this.map.has(key);
	}
	get(key) {
		const node = this.getNode(key);
		return node && node.value;
	}
	getNode(key) {
		const node = this.map.get(key);
		if (node && node !== this.newest) {
			const { older, newer } = node;
			if (newer) newer.older = older;
			if (older) older.newer = newer;
			node.older = this.newest;
			node.older.newer = node;
			node.newer = null;
			this.newest = node;
			if (node === this.oldest) this.oldest = newer;
		}
		return node;
	}
	set(key, value) {
		let node = this.getNode(key);
		if (node) return node.value = value;
		node = {
			key,
			value,
			newer: null,
			older: this.newest
		};
		if (this.newest) this.newest.newer = node;
		this.newest = node;
		this.oldest = this.oldest || node;
		this.scheduleFinalization(node);
		this.map.set(key, node);
		this.size++;
		return node.value;
	}
	clean() {
		while (this.oldest && this.size > this.max) this.deleteNode(this.oldest);
	}
	deleteNode(node) {
		if (node === this.newest) this.newest = node.older;
		if (node === this.oldest) this.oldest = node.newer;
		if (node.newer) node.newer.older = node.older;
		if (node.older) node.older.newer = node.newer;
		this.size--;
		const key = node.key || node.keyRef && node.keyRef.deref();
		this.dispose(node.value, key);
		if (!node.keyRef) this.unfinalizedNodes.delete(node);
		else this.registry.unregister(node);
		if (key) this.map.delete(key);
	}
	delete(key) {
		const node = this.map.get(key);
		if (node) {
			this.deleteNode(node);
			return true;
		}
		return false;
	}
	scheduleFinalization(node) {
		this.unfinalizedNodes.add(node);
		if (!this.finalizationScheduled) {
			this.finalizationScheduled = true;
			queueMicrotask(this.finalize);
		}
	}
};
//#endregion
//#region node_modules/@apollo/client/utilities/caching/caches.js
var scheduledCleanup = /* @__PURE__ */ new WeakSet();
function schedule(cache) {
	if (cache.size <= (cache.max || -1)) return;
	if (!scheduledCleanup.has(cache)) {
		scheduledCleanup.add(cache);
		setTimeout(function() {
			cache.clean();
			scheduledCleanup.delete(cache);
		}, 100);
	}
}
/**
* @internal
* A version of WeakCache that will auto-schedule a cleanup of the cache when
* a new item is added and the cache reached maximum size.
* Throttled to once per 100ms.
*
* @privateRemarks
* Should be used throughout the rest of the codebase instead of WeakCache,
* with the notable exception of usage in `wrap` from `optimism` - that one
* already handles cleanup and should remain a `WeakCache`.
*/
var AutoCleanedWeakCache = function(max, dispose) {
	var cache = new WeakCache(max, dispose);
	cache.set = function(key, value) {
		var ret = WeakCache.prototype.set.call(this, key, value);
		schedule(this);
		return ret;
	};
	return cache;
};
/**
* @internal
* A version of StrongCache that will auto-schedule a cleanup of the cache when
* a new item is added and the cache reached maximum size.
* Throttled to once per 100ms.
*
* @privateRemarks
* Should be used throughout the rest of the codebase instead of StrongCache,
* with the notable exception of usage in `wrap` from `optimism` - that one
* already handles cleanup and should remain a `StrongCache`.
*/
var AutoCleanedStrongCache = function(max, dispose) {
	var cache = new StrongCache(max, dispose);
	cache.set = function(key, value) {
		var ret = StrongCache.prototype.set.call(this, key, value);
		schedule(this);
		return ret;
	};
	return cache;
};
/**
*
* The global cache size configuration for Apollo Client.
*
* @remarks
*
* You can directly modify this object, but any modification will
* only have an effect on caches that are created after the modification.
*
* So for global caches, such as `parser`, `canonicalStringify` and `print`,
* you might need to call `.reset` on them, which will essentially re-create them.
*
* Alternatively, you can set `globalThis[Symbol.for("apollo.cacheSize")]` before
* you load the Apollo Client package:
*
* @example
* ```ts
* globalThis[Symbol.for("apollo.cacheSize")] = {
*   parser: 100
* } satisfies Partial<CacheSizes> // the `satisfies` is optional if using TypeScript
* ```
*/
var cacheSizes = __assign({}, global_default[Symbol.for("apollo.cacheSize")]);
//#endregion
//#region node_modules/@apollo/client/utilities/caching/getMemoryInternals.js
var globalCaches = {};
function registerGlobalCache(name, getSize) {
	globalCaches[name] = getSize;
}
/**
* For internal purposes only - please call `ApolloClient.getMemoryInternals` instead
* @internal
*/
var getApolloClientMemoryInternals = globalThis.__DEV__ !== false ? _getApolloClientMemoryInternals : void 0;
/**
* For internal purposes only - please call `ApolloClient.getMemoryInternals` instead
* @internal
*/
var getInMemoryCacheMemoryInternals = globalThis.__DEV__ !== false ? _getInMemoryCacheMemoryInternals : void 0;
/**
* For internal purposes only - please call `ApolloClient.getMemoryInternals` instead
* @internal
*/
var getApolloCacheMemoryInternals = globalThis.__DEV__ !== false ? _getApolloCacheMemoryInternals : void 0;
function getCurrentCacheSizes() {
	return Object.fromEntries(Object.entries({
		parser: 1e3,
		canonicalStringify: 1e3,
		print: 2e3,
		"documentTransform.cache": 2e3,
		"queryManager.getDocumentInfo": 2e3,
		"PersistedQueryLink.persistedQueryHashes": 2e3,
		"fragmentRegistry.transform": 2e3,
		"fragmentRegistry.lookup": 1e3,
		"fragmentRegistry.findFragmentSpreads": 4e3,
		"cache.fragmentQueryDocuments": 1e3,
		"removeTypenameFromVariables.getVariableDefinitions": 2e3,
		"inMemoryCache.maybeBroadcastWatch": 5e3,
		"inMemoryCache.executeSelectionSet": 5e4,
		"inMemoryCache.executeSubSelectedArray": 1e4
	}).map(function(_a) {
		var k = _a[0], v = _a[1];
		return [k, cacheSizes[k] || v];
	}));
}
function _getApolloClientMemoryInternals() {
	var _a, _b, _c, _d, _e;
	if (!(globalThis.__DEV__ !== false)) throw new Error("only supported in development mode");
	return {
		limits: getCurrentCacheSizes(),
		sizes: __assign({
			print: (_a = globalCaches.print) === null || _a === void 0 ? void 0 : _a.call(globalCaches),
			parser: (_b = globalCaches.parser) === null || _b === void 0 ? void 0 : _b.call(globalCaches),
			canonicalStringify: (_c = globalCaches.canonicalStringify) === null || _c === void 0 ? void 0 : _c.call(globalCaches),
			links: linkInfo(this.link),
			queryManager: {
				getDocumentInfo: this["queryManager"]["transformCache"].size,
				documentTransforms: transformInfo(this["queryManager"].documentTransform)
			}
		}, (_e = (_d = this.cache).getMemoryInternals) === null || _e === void 0 ? void 0 : _e.call(_d))
	};
}
function _getApolloCacheMemoryInternals() {
	return { cache: { fragmentQueryDocuments: getWrapperInformation(this["getFragmentDoc"]) } };
}
function _getInMemoryCacheMemoryInternals() {
	var fragments = this.config.fragments;
	return __assign(__assign({}, _getApolloCacheMemoryInternals.apply(this)), {
		addTypenameDocumentTransform: transformInfo(this["addTypenameTransform"]),
		inMemoryCache: {
			executeSelectionSet: getWrapperInformation(this["storeReader"]["executeSelectionSet"]),
			executeSubSelectedArray: getWrapperInformation(this["storeReader"]["executeSubSelectedArray"]),
			maybeBroadcastWatch: getWrapperInformation(this["maybeBroadcastWatch"])
		},
		fragmentRegistry: {
			findFragmentSpreads: getWrapperInformation(fragments === null || fragments === void 0 ? void 0 : fragments.findFragmentSpreads),
			lookup: getWrapperInformation(fragments === null || fragments === void 0 ? void 0 : fragments.lookup),
			transform: getWrapperInformation(fragments === null || fragments === void 0 ? void 0 : fragments.transform)
		}
	});
}
function isWrapper(f) {
	return !!f && "dirtyKey" in f;
}
function getWrapperInformation(f) {
	return isWrapper(f) ? f.size : void 0;
}
function isDefined(value) {
	return value != null;
}
function transformInfo(transform) {
	return recurseTransformInfo(transform).map(function(cache) {
		return { cache };
	});
}
function recurseTransformInfo(transform) {
	return transform ? __spreadArray(__spreadArray([getWrapperInformation(transform === null || transform === void 0 ? void 0 : transform["performWork"])], recurseTransformInfo(transform === null || transform === void 0 ? void 0 : transform["left"]), true), recurseTransformInfo(transform === null || transform === void 0 ? void 0 : transform["right"]), true).filter(isDefined) : [];
}
function linkInfo(link) {
	var _a;
	return link ? __spreadArray(__spreadArray([(_a = link === null || link === void 0 ? void 0 : link.getMemoryInternals) === null || _a === void 0 ? void 0 : _a.call(link)], linkInfo(link === null || link === void 0 ? void 0 : link.left), true), linkInfo(link === null || link === void 0 ? void 0 : link.right), true).filter(isDefined) : [];
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/canonicalStringify.js
/**
* Like JSON.stringify, but with object keys always sorted in the same order.
*
* To achieve performant sorting, this function uses a Map from JSON-serialized
* arrays of keys (in any order) to sorted arrays of the same keys, with a
* single sorted array reference shared by all permutations of the keys.
*
* As a drawback, this function will add a little bit more memory for every
* object encountered that has different (more, less, a different order of) keys
* than in the past.
*
* In a typical application, this extra memory usage should not play a
* significant role, as `canonicalStringify` will be called for only a limited
* number of object shapes, and the cache will not grow beyond a certain point.
* But in some edge cases, this could be a problem, so we provide
* canonicalStringify.reset() as a way of clearing the cache.
* */
var canonicalStringify = Object.assign(function canonicalStringify(value) {
	return JSON.stringify(value, stableObjectReplacer);
}, { reset: function() {
	sortingMap = new AutoCleanedStrongCache(cacheSizes.canonicalStringify || 1e3);
} });
if (globalThis.__DEV__ !== false) registerGlobalCache("canonicalStringify", function() {
	return sortingMap.size;
});
var sortingMap;
canonicalStringify.reset();
function stableObjectReplacer(key, value) {
	if (value && typeof value === "object") {
		var proto = Object.getPrototypeOf(value);
		if (proto === Object.prototype || proto === null) {
			var keys = Object.keys(value);
			if (keys.every(everyKeyInOrder)) return value;
			var unsortedKey = JSON.stringify(keys);
			var sortedKeys = sortingMap.get(unsortedKey);
			if (!sortedKeys) {
				keys.sort();
				var sortedKey = JSON.stringify(keys);
				sortedKeys = sortingMap.get(sortedKey) || keys;
				sortingMap.set(unsortedKey, sortedKeys);
				sortingMap.set(sortedKey, sortedKeys);
			}
			var sortedObject_1 = Object.create(proto);
			sortedKeys.forEach(function(key) {
				sortedObject_1[key] = value[key];
			});
			return sortedObject_1;
		}
	}
	return value;
}
function everyKeyInOrder(key, i, keys) {
	return i === 0 || keys[i - 1] <= key;
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/storeUtils.js
function makeReference(id) {
	return { __ref: String(id) };
}
function isReference(obj) {
	return Boolean(obj && typeof obj === "object" && typeof obj.__ref === "string");
}
function isDocumentNode(value) {
	return isNonNullObject(value) && value.kind === "Document" && Array.isArray(value.definitions);
}
function isStringValue(value) {
	return value.kind === "StringValue";
}
function isBooleanValue(value) {
	return value.kind === "BooleanValue";
}
function isIntValue(value) {
	return value.kind === "IntValue";
}
function isFloatValue(value) {
	return value.kind === "FloatValue";
}
function isVariable(value) {
	return value.kind === "Variable";
}
function isObjectValue(value) {
	return value.kind === "ObjectValue";
}
function isListValue(value) {
	return value.kind === "ListValue";
}
function isEnumValue(value) {
	return value.kind === "EnumValue";
}
function isNullValue(value) {
	return value.kind === "NullValue";
}
function valueToObjectRepresentation(argObj, name, value, variables) {
	if (isIntValue(value) || isFloatValue(value)) argObj[name.value] = Number(value.value);
	else if (isBooleanValue(value) || isStringValue(value)) argObj[name.value] = value.value;
	else if (isObjectValue(value)) {
		var nestedArgObj_1 = {};
		value.fields.map(function(obj) {
			return valueToObjectRepresentation(nestedArgObj_1, obj.name, obj.value, variables);
		});
		argObj[name.value] = nestedArgObj_1;
	} else if (isVariable(value)) {
		var variableValue = (variables || {})[value.name.value];
		argObj[name.value] = variableValue;
	} else if (isListValue(value)) argObj[name.value] = value.values.map(function(listValue) {
		var nestedArgArrayObj = {};
		valueToObjectRepresentation(nestedArgArrayObj, name, listValue, variables);
		return nestedArgArrayObj[name.value];
	});
	else if (isEnumValue(value)) argObj[name.value] = value.value;
	else if (isNullValue(value)) argObj[name.value] = null;
	else throw newInvariantError(124, name.value, value.kind);
}
function storeKeyNameFromField(field, variables) {
	var directivesObj = null;
	if (field.directives) {
		directivesObj = {};
		field.directives.forEach(function(directive) {
			directivesObj[directive.name.value] = {};
			if (directive.arguments) directive.arguments.forEach(function(_a) {
				var name = _a.name, value = _a.value;
				return valueToObjectRepresentation(directivesObj[directive.name.value], name, value, variables);
			});
		});
	}
	var argObj = null;
	if (field.arguments && field.arguments.length) {
		argObj = {};
		field.arguments.forEach(function(_a) {
			var name = _a.name, value = _a.value;
			return valueToObjectRepresentation(argObj, name, value, variables);
		});
	}
	return getStoreKeyName(field.name.value, argObj, directivesObj);
}
var KNOWN_DIRECTIVES = [
	"connection",
	"include",
	"skip",
	"client",
	"rest",
	"export",
	"nonreactive"
];
var storeKeyNameStringify = canonicalStringify;
var getStoreKeyName = Object.assign(function(fieldName, args, directives) {
	if (args && directives && directives["connection"] && directives["connection"]["key"]) if (directives["connection"]["filter"] && directives["connection"]["filter"].length > 0) {
		var filterKeys = directives["connection"]["filter"] ? directives["connection"]["filter"] : [];
		filterKeys.sort();
		var filteredArgs_1 = {};
		filterKeys.forEach(function(key) {
			filteredArgs_1[key] = args[key];
		});
		return "".concat(directives["connection"]["key"], "(").concat(storeKeyNameStringify(filteredArgs_1), ")");
	} else return directives["connection"]["key"];
	var completeFieldName = fieldName;
	if (args) {
		var stringifiedArgs = storeKeyNameStringify(args);
		completeFieldName += "(".concat(stringifiedArgs, ")");
	}
	if (directives) Object.keys(directives).forEach(function(key) {
		if (KNOWN_DIRECTIVES.indexOf(key) !== -1) return;
		if (directives[key] && Object.keys(directives[key]).length) completeFieldName += "@".concat(key, "(").concat(storeKeyNameStringify(directives[key]), ")");
		else completeFieldName += "@".concat(key);
	});
	return completeFieldName;
}, { setStringify: function(s) {
	var previous = storeKeyNameStringify;
	storeKeyNameStringify = s;
	return previous;
} });
function argumentsObjectFromField(field, variables) {
	if (field.arguments && field.arguments.length) {
		var argObj_1 = {};
		field.arguments.forEach(function(_a) {
			var name = _a.name, value = _a.value;
			return valueToObjectRepresentation(argObj_1, name, value, variables);
		});
		return argObj_1;
	}
	return null;
}
function resultKeyNameFromField(field) {
	return field.alias ? field.alias.value : field.name.value;
}
function getTypenameFromResult(result, selectionSet, fragmentMap) {
	var fragments;
	for (var _i = 0, _a = selectionSet.selections; _i < _a.length; _i++) {
		var selection = _a[_i];
		if (isField(selection)) {
			if (selection.name.value === "__typename") return result[resultKeyNameFromField(selection)];
		} else if (fragments) fragments.push(selection);
		else fragments = [selection];
	}
	if (typeof result.__typename === "string") return result.__typename;
	if (fragments) for (var _b = 0, fragments_1 = fragments; _b < fragments_1.length; _b++) {
		var selection = fragments_1[_b];
		var typename = getTypenameFromResult(result, getFragmentFromSelection(selection, fragmentMap).selectionSet, fragmentMap);
		if (typeof typename === "string") return typename;
	}
}
function isField(selection) {
	return selection.kind === "Field";
}
function isInlineFragment(selection) {
	return selection.kind === "InlineFragment";
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/getFromAST.js
function checkDocument(doc) {
	invariant$1(doc && doc.kind === "Document", 116);
	var operations = doc.definitions.filter(function(d) {
		return d.kind !== "FragmentDefinition";
	}).map(function(definition) {
		if (definition.kind !== "OperationDefinition") throw newInvariantError(117, definition.kind);
		return definition;
	});
	invariant$1(operations.length <= 1, 118, operations.length);
	return doc;
}
function getOperationDefinition(doc) {
	checkDocument(doc);
	return doc.definitions.filter(function(definition) {
		return definition.kind === "OperationDefinition";
	})[0];
}
function getOperationName(doc) {
	return doc.definitions.filter(function(definition) {
		return definition.kind === "OperationDefinition" && !!definition.name;
	}).map(function(x) {
		return x.name.value;
	})[0] || null;
}
function getFragmentDefinitions(doc) {
	return doc.definitions.filter(function(definition) {
		return definition.kind === "FragmentDefinition";
	});
}
function getQueryDefinition(doc) {
	var queryDef = getOperationDefinition(doc);
	invariant$1(queryDef && queryDef.operation === "query", 119);
	return queryDef;
}
function getFragmentDefinition(doc) {
	invariant$1(doc.kind === "Document", 120);
	invariant$1(doc.definitions.length <= 1, 121);
	var fragmentDef = doc.definitions[0];
	invariant$1(fragmentDef.kind === "FragmentDefinition", 122);
	return fragmentDef;
}
/**
* Returns the first operation definition found in this document.
* If no operation definition is found, the first fragment definition will be returned.
* If no definitions are found, an error will be thrown.
*/
function getMainDefinition(queryDoc) {
	checkDocument(queryDoc);
	var fragmentDefinition;
	for (var _i = 0, _a = queryDoc.definitions; _i < _a.length; _i++) {
		var definition = _a[_i];
		if (definition.kind === "OperationDefinition") {
			var operation = definition.operation;
			if (operation === "query" || operation === "mutation" || operation === "subscription") return definition;
		}
		if (definition.kind === "FragmentDefinition" && !fragmentDefinition) fragmentDefinition = definition;
	}
	if (fragmentDefinition) return fragmentDefinition;
	throw newInvariantError(123);
}
function getDefaultValues(definition) {
	var defaultValues = Object.create(null);
	var defs = definition && definition.variableDefinitions;
	if (defs && defs.length) defs.forEach(function(def) {
		if (def.defaultValue) valueToObjectRepresentation(defaultValues, def.variable.name, def.defaultValue);
	});
	return defaultValues;
}
//#endregion
//#region node_modules/@wry/context/lib/slot.js
var currentContext = null;
var MISSING_VALUE = {};
var idCounter = 1;
var makeSlotClass = () => class Slot {
	constructor() {
		this.id = [
			"slot",
			idCounter++,
			Date.now(),
			Math.random().toString(36).slice(2)
		].join(":");
	}
	hasValue() {
		for (let context = currentContext; context; context = context.parent) if (this.id in context.slots) {
			const value = context.slots[this.id];
			if (value === MISSING_VALUE) break;
			if (context !== currentContext) currentContext.slots[this.id] = value;
			return true;
		}
		if (currentContext) currentContext.slots[this.id] = MISSING_VALUE;
		return false;
	}
	getValue() {
		if (this.hasValue()) return currentContext.slots[this.id];
	}
	withValue(value, callback, args, thisArg) {
		const slots = {
			__proto__: null,
			[this.id]: value
		};
		const parent = currentContext;
		currentContext = {
			parent,
			slots
		};
		try {
			return callback.apply(thisArg, args);
		} finally {
			currentContext = parent;
		}
	}
	static bind(callback) {
		const context = currentContext;
		return function() {
			const saved = currentContext;
			try {
				currentContext = context;
				return callback.apply(this, arguments);
			} finally {
				currentContext = saved;
			}
		};
	}
	static noContext(callback, args, thisArg) {
		if (currentContext) {
			const saved = currentContext;
			try {
				currentContext = null;
				return callback.apply(thisArg, args);
			} finally {
				currentContext = saved;
			}
		} else return callback.apply(thisArg, args);
	}
};
function maybe(fn) {
	try {
		return fn();
	} catch (ignored) {}
}
var globalKey = "@wry/context:Slot";
var globalHost = maybe(() => globalThis) || maybe(() => global) || Object.create(null);
var Slot = globalHost[globalKey] || Array[globalKey] || (function(Slot) {
	try {
		Object.defineProperty(globalHost, globalKey, {
			value: Slot,
			enumerable: false,
			writable: false,
			configurable: true
		});
	} finally {
		return Slot;
	}
})(makeSlotClass());
//#endregion
//#region node_modules/@wry/context/lib/index.js
var { bind, noContext } = Slot;
//#endregion
//#region node_modules/optimism/lib/context.js
var parentEntrySlot = new Slot();
//#endregion
//#region node_modules/optimism/lib/helpers.js
var { hasOwnProperty: hasOwnProperty$5 } = Object.prototype;
var arrayFromSet = Array.from || function(set) {
	const array = [];
	set.forEach((item) => array.push(item));
	return array;
};
function maybeUnsubscribe(entryOrDep) {
	const { unsubscribe } = entryOrDep;
	if (typeof unsubscribe === "function") {
		entryOrDep.unsubscribe = void 0;
		unsubscribe();
	}
}
//#endregion
//#region node_modules/optimism/lib/entry.js
var emptySetPool = [];
var POOL_TARGET_SIZE = 100;
function assert$1(condition, optionalMessage) {
	if (!condition) throw new Error(optionalMessage || "assertion failure");
}
function valueIs(a, b) {
	const len = a.length;
	return len > 0 && len === b.length && a[len - 1] === b[len - 1];
}
function valueGet(value) {
	switch (value.length) {
		case 0: throw new Error("unknown value");
		case 1: return value[0];
		case 2: throw value[1];
	}
}
function valueCopy(value) {
	return value.slice(0);
}
var Entry = class Entry {
	constructor(fn) {
		this.fn = fn;
		this.parents = /* @__PURE__ */ new Set();
		this.childValues = /* @__PURE__ */ new Map();
		this.dirtyChildren = null;
		this.dirty = true;
		this.recomputing = false;
		this.value = [];
		this.deps = null;
		++Entry.count;
	}
	peek() {
		if (this.value.length === 1 && !mightBeDirty(this)) {
			rememberParent(this);
			return this.value[0];
		}
	}
	recompute(args) {
		assert$1(!this.recomputing, "already recomputing");
		rememberParent(this);
		return mightBeDirty(this) ? reallyRecompute(this, args) : valueGet(this.value);
	}
	setDirty() {
		if (this.dirty) return;
		this.dirty = true;
		reportDirty(this);
		maybeUnsubscribe(this);
	}
	dispose() {
		this.setDirty();
		forgetChildren(this);
		eachParent(this, (parent, child) => {
			parent.setDirty();
			forgetChild(parent, this);
		});
	}
	forget() {
		this.dispose();
	}
	dependOn(dep) {
		dep.add(this);
		if (!this.deps) this.deps = emptySetPool.pop() || /* @__PURE__ */ new Set();
		this.deps.add(dep);
	}
	forgetDeps() {
		if (this.deps) {
			arrayFromSet(this.deps).forEach((dep) => dep.delete(this));
			this.deps.clear();
			emptySetPool.push(this.deps);
			this.deps = null;
		}
	}
};
Entry.count = 0;
function rememberParent(child) {
	const parent = parentEntrySlot.getValue();
	if (parent) {
		child.parents.add(parent);
		if (!parent.childValues.has(child)) parent.childValues.set(child, []);
		if (mightBeDirty(child)) reportDirtyChild(parent, child);
		else reportCleanChild(parent, child);
		return parent;
	}
}
function reallyRecompute(entry, args) {
	forgetChildren(entry);
	parentEntrySlot.withValue(entry, recomputeNewValue, [entry, args]);
	if (maybeSubscribe(entry, args)) setClean(entry);
	return valueGet(entry.value);
}
function recomputeNewValue(entry, args) {
	entry.recomputing = true;
	const { normalizeResult } = entry;
	let oldValueCopy;
	if (normalizeResult && entry.value.length === 1) oldValueCopy = valueCopy(entry.value);
	entry.value.length = 0;
	try {
		entry.value[0] = entry.fn.apply(null, args);
		if (normalizeResult && oldValueCopy && !valueIs(oldValueCopy, entry.value)) try {
			entry.value[0] = normalizeResult(entry.value[0], oldValueCopy[0]);
		} catch (_a) {}
	} catch (e) {
		entry.value[1] = e;
	}
	entry.recomputing = false;
}
function mightBeDirty(entry) {
	return entry.dirty || !!(entry.dirtyChildren && entry.dirtyChildren.size);
}
function setClean(entry) {
	entry.dirty = false;
	if (mightBeDirty(entry)) return;
	reportClean(entry);
}
function reportDirty(child) {
	eachParent(child, reportDirtyChild);
}
function reportClean(child) {
	eachParent(child, reportCleanChild);
}
function eachParent(child, callback) {
	const parentCount = child.parents.size;
	if (parentCount) {
		const parents = arrayFromSet(child.parents);
		for (let i = 0; i < parentCount; ++i) callback(parents[i], child);
	}
}
function reportDirtyChild(parent, child) {
	assert$1(parent.childValues.has(child));
	assert$1(mightBeDirty(child));
	const parentWasClean = !mightBeDirty(parent);
	if (!parent.dirtyChildren) parent.dirtyChildren = emptySetPool.pop() || /* @__PURE__ */ new Set();
	else if (parent.dirtyChildren.has(child)) return;
	parent.dirtyChildren.add(child);
	if (parentWasClean) reportDirty(parent);
}
function reportCleanChild(parent, child) {
	assert$1(parent.childValues.has(child));
	assert$1(!mightBeDirty(child));
	const childValue = parent.childValues.get(child);
	if (childValue.length === 0) parent.childValues.set(child, valueCopy(child.value));
	else if (!valueIs(childValue, child.value)) parent.setDirty();
	removeDirtyChild(parent, child);
	if (mightBeDirty(parent)) return;
	reportClean(parent);
}
function removeDirtyChild(parent, child) {
	const dc = parent.dirtyChildren;
	if (dc) {
		dc.delete(child);
		if (dc.size === 0) {
			if (emptySetPool.length < POOL_TARGET_SIZE) emptySetPool.push(dc);
			parent.dirtyChildren = null;
		}
	}
}
function forgetChildren(parent) {
	if (parent.childValues.size > 0) parent.childValues.forEach((_value, child) => {
		forgetChild(parent, child);
	});
	parent.forgetDeps();
	assert$1(parent.dirtyChildren === null);
}
function forgetChild(parent, child) {
	child.parents.delete(parent);
	parent.childValues.delete(child);
	removeDirtyChild(parent, child);
}
function maybeSubscribe(entry, args) {
	if (typeof entry.subscribe === "function") try {
		maybeUnsubscribe(entry);
		entry.unsubscribe = entry.subscribe.apply(null, args);
	} catch (e) {
		entry.setDirty();
		return false;
	}
	return true;
}
//#endregion
//#region node_modules/optimism/lib/dep.js
var EntryMethods = {
	setDirty: true,
	dispose: true,
	forget: true
};
function dep(options) {
	const depsByKey = /* @__PURE__ */ new Map();
	const subscribe = options && options.subscribe;
	function depend(key) {
		const parent = parentEntrySlot.getValue();
		if (parent) {
			let dep = depsByKey.get(key);
			if (!dep) depsByKey.set(key, dep = /* @__PURE__ */ new Set());
			parent.dependOn(dep);
			if (typeof subscribe === "function") {
				maybeUnsubscribe(dep);
				dep.unsubscribe = subscribe(key);
			}
		}
	}
	depend.dirty = function dirty(key, entryMethodName) {
		const dep = depsByKey.get(key);
		if (dep) {
			const m = entryMethodName && hasOwnProperty$5.call(EntryMethods, entryMethodName) ? entryMethodName : "setDirty";
			arrayFromSet(dep).forEach((entry) => entry[m]());
			depsByKey.delete(key);
			maybeUnsubscribe(dep);
		}
	};
	return depend;
}
//#endregion
//#region node_modules/optimism/lib/index.js
var defaultKeyTrie;
function defaultMakeCacheKey(...args) {
	return (defaultKeyTrie || (defaultKeyTrie = new Trie(typeof WeakMap === "function"))).lookupArray(args);
}
var caches = /* @__PURE__ */ new Set();
function wrap(originalFunction, { max = Math.pow(2, 16), keyArgs, makeCacheKey = defaultMakeCacheKey, normalizeResult, subscribe, cache: cacheOption = StrongCache } = Object.create(null)) {
	const cache = typeof cacheOption === "function" ? new cacheOption(max, (entry) => entry.dispose()) : cacheOption;
	const optimistic = function() {
		const key = makeCacheKey.apply(null, keyArgs ? keyArgs.apply(null, arguments) : arguments);
		if (key === void 0) return originalFunction.apply(null, arguments);
		let entry = cache.get(key);
		if (!entry) {
			cache.set(key, entry = new Entry(originalFunction));
			entry.normalizeResult = normalizeResult;
			entry.subscribe = subscribe;
			entry.forget = () => cache.delete(key);
		}
		const value = entry.recompute(Array.prototype.slice.call(arguments));
		cache.set(key, entry);
		caches.add(cache);
		if (!parentEntrySlot.hasValue()) {
			caches.forEach((cache) => cache.clean());
			caches.clear();
		}
		return value;
	};
	Object.defineProperty(optimistic, "size", {
		get: () => cache.size,
		configurable: false,
		enumerable: false
	});
	Object.freeze(optimistic.options = {
		max,
		keyArgs,
		makeCacheKey,
		normalizeResult,
		subscribe,
		cache
	});
	function dirtyKey(key) {
		const entry = key && cache.get(key);
		if (entry) entry.setDirty();
	}
	optimistic.dirtyKey = dirtyKey;
	optimistic.dirty = function dirty() {
		dirtyKey(makeCacheKey.apply(null, arguments));
	};
	function peekKey(key) {
		const entry = key && cache.get(key);
		if (entry) return entry.peek();
	}
	optimistic.peekKey = peekKey;
	optimistic.peek = function peek() {
		return peekKey(makeCacheKey.apply(null, arguments));
	};
	function forgetKey(key) {
		return key ? cache.delete(key) : false;
	}
	optimistic.forgetKey = forgetKey;
	optimistic.forget = function forget() {
		return forgetKey(makeCacheKey.apply(null, arguments));
	};
	optimistic.makeCacheKey = makeCacheKey;
	optimistic.getKey = keyArgs ? function getKey() {
		return makeCacheKey.apply(null, keyArgs.apply(null, arguments));
	} : makeCacheKey;
	return Object.freeze(optimistic);
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/DocumentTransform.js
function identity(document) {
	return document;
}
var DocumentTransform = function() {
	function DocumentTransform(transform, options) {
		if (options === void 0) options = Object.create(null);
		this.resultCache = canUseWeakSet ? /* @__PURE__ */ new WeakSet() : /* @__PURE__ */ new Set();
		this.transform = transform;
		if (options.getCacheKey) this.getCacheKey = options.getCacheKey;
		this.cached = options.cache !== false;
		this.resetCache();
	}
	DocumentTransform.prototype.getCacheKey = function(document) {
		return [document];
	};
	DocumentTransform.identity = function() {
		return new DocumentTransform(identity, { cache: false });
	};
	DocumentTransform.split = function(predicate, left, right) {
		if (right === void 0) right = DocumentTransform.identity();
		return Object.assign(new DocumentTransform(function(document) {
			return (predicate(document) ? left : right).transformDocument(document);
		}, { cache: false }), {
			left,
			right
		});
	};
	/**
	* Resets the internal cache of this transform, if it has one.
	*/
	DocumentTransform.prototype.resetCache = function() {
		var _this = this;
		if (this.cached) {
			var stableCacheKeys_1 = new Trie(canUseWeakMap);
			this.performWork = wrap(DocumentTransform.prototype.performWork.bind(this), {
				makeCacheKey: function(document) {
					var cacheKeys = _this.getCacheKey(document);
					if (cacheKeys) {
						invariant$1(Array.isArray(cacheKeys), 105);
						return stableCacheKeys_1.lookupArray(cacheKeys);
					}
				},
				max: cacheSizes["documentTransform.cache"],
				cache: WeakCache
			});
		}
	};
	DocumentTransform.prototype.performWork = function(document) {
		checkDocument(document);
		return this.transform(document);
	};
	DocumentTransform.prototype.transformDocument = function(document) {
		if (this.resultCache.has(document)) return document;
		var transformedDocument = this.performWork(document);
		this.resultCache.add(transformedDocument);
		return transformedDocument;
	};
	DocumentTransform.prototype.concat = function(otherTransform) {
		var _this = this;
		return Object.assign(new DocumentTransform(function(document) {
			return otherTransform.transformDocument(_this.transformDocument(document));
		}, { cache: false }), {
			left: this,
			right: otherTransform
		});
	};
	return DocumentTransform;
}();
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/print.js
var printCache;
var print = Object.assign(function(ast) {
	var result = printCache.get(ast);
	if (!result) {
		result = print$1(ast);
		printCache.set(ast, result);
	}
	return result;
}, { reset: function() {
	printCache = new AutoCleanedWeakCache(cacheSizes.print || 2e3);
} });
print.reset();
if (globalThis.__DEV__ !== false) registerGlobalCache("print", function() {
	return printCache ? printCache.size : 0;
});
//#endregion
//#region node_modules/@apollo/client/utilities/common/arrays.js
var isArray = Array.isArray;
function isNonEmptyArray(value) {
	return Array.isArray(value) && value.length > 0;
}
//#endregion
//#region node_modules/@apollo/client/utilities/graphql/transform.js
var TYPENAME_FIELD = {
	kind: Kind.FIELD,
	name: {
		kind: Kind.NAME,
		value: "__typename"
	}
};
function isEmpty(op, fragmentMap) {
	return !op || op.selectionSet.selections.every(function(selection) {
		return selection.kind === Kind.FRAGMENT_SPREAD && isEmpty(fragmentMap[selection.name.value], fragmentMap);
	});
}
function nullIfDocIsEmpty(doc) {
	return isEmpty(getOperationDefinition(doc) || getFragmentDefinition(doc), createFragmentMap(getFragmentDefinitions(doc))) ? null : doc;
}
function getDirectiveMatcher(configs) {
	var names = /* @__PURE__ */ new Map();
	var tests = /* @__PURE__ */ new Map();
	configs.forEach(function(directive) {
		if (directive) {
			if (directive.name) names.set(directive.name, directive);
			else if (directive.test) tests.set(directive.test, directive);
		}
	});
	return function(directive) {
		var config = names.get(directive.name.value);
		if (!config && tests.size) tests.forEach(function(testConfig, test) {
			if (test(directive)) config = testConfig;
		});
		return config;
	};
}
function makeInUseGetterFunction(defaultKey) {
	var map = /* @__PURE__ */ new Map();
	return function inUseGetterFunction(key) {
		if (key === void 0) key = defaultKey;
		var inUse = map.get(key);
		if (!inUse) map.set(key, inUse = {
			variables: /* @__PURE__ */ new Set(),
			fragmentSpreads: /* @__PURE__ */ new Set()
		});
		return inUse;
	};
}
function removeDirectivesFromDocument(directives, doc) {
	checkDocument(doc);
	var getInUseByOperationName = makeInUseGetterFunction("");
	var getInUseByFragmentName = makeInUseGetterFunction("");
	var getInUse = function(ancestors) {
		for (var p = 0, ancestor = void 0; p < ancestors.length && (ancestor = ancestors[p]); ++p) {
			if (isArray(ancestor)) continue;
			if (ancestor.kind === Kind.OPERATION_DEFINITION) return getInUseByOperationName(ancestor.name && ancestor.name.value);
			if (ancestor.kind === Kind.FRAGMENT_DEFINITION) return getInUseByFragmentName(ancestor.name.value);
		}
		globalThis.__DEV__ !== false && invariant$1.error(125);
		return null;
	};
	var operationCount = 0;
	for (var i = doc.definitions.length - 1; i >= 0; --i) if (doc.definitions[i].kind === Kind.OPERATION_DEFINITION) ++operationCount;
	var directiveMatcher = getDirectiveMatcher(directives);
	var shouldRemoveField = function(nodeDirectives) {
		return isNonEmptyArray(nodeDirectives) && nodeDirectives.map(directiveMatcher).some(function(config) {
			return config && config.remove;
		});
	};
	var originalFragmentDefsByPath = /* @__PURE__ */ new Map();
	var firstVisitMadeChanges = false;
	var fieldOrInlineFragmentVisitor = { enter: function(node) {
		if (shouldRemoveField(node.directives)) {
			firstVisitMadeChanges = true;
			return null;
		}
	} };
	var docWithoutDirectiveSubtrees = visit(doc, {
		Field: fieldOrInlineFragmentVisitor,
		InlineFragment: fieldOrInlineFragmentVisitor,
		VariableDefinition: { enter: function() {
			return false;
		} },
		Variable: { enter: function(node, _key, _parent, _path, ancestors) {
			var inUse = getInUse(ancestors);
			if (inUse) inUse.variables.add(node.name.value);
		} },
		FragmentSpread: { enter: function(node, _key, _parent, _path, ancestors) {
			if (shouldRemoveField(node.directives)) {
				firstVisitMadeChanges = true;
				return null;
			}
			var inUse = getInUse(ancestors);
			if (inUse) inUse.fragmentSpreads.add(node.name.value);
		} },
		FragmentDefinition: {
			enter: function(node, _key, _parent, path) {
				originalFragmentDefsByPath.set(JSON.stringify(path), node);
			},
			leave: function(node, _key, _parent, path) {
				if (node === originalFragmentDefsByPath.get(JSON.stringify(path))) return node;
				if (operationCount > 0 && node.selectionSet.selections.every(function(selection) {
					return selection.kind === Kind.FIELD && selection.name.value === "__typename";
				})) {
					getInUseByFragmentName(node.name.value).removed = true;
					firstVisitMadeChanges = true;
					return null;
				}
			}
		},
		Directive: { leave: function(node) {
			if (directiveMatcher(node)) {
				firstVisitMadeChanges = true;
				return null;
			}
		} }
	});
	if (!firstVisitMadeChanges) return doc;
	var populateTransitiveVars = function(inUse) {
		if (!inUse.transitiveVars) {
			inUse.transitiveVars = new Set(inUse.variables);
			if (!inUse.removed) inUse.fragmentSpreads.forEach(function(childFragmentName) {
				populateTransitiveVars(getInUseByFragmentName(childFragmentName)).transitiveVars.forEach(function(varName) {
					inUse.transitiveVars.add(varName);
				});
			});
		}
		return inUse;
	};
	var allFragmentNamesUsed = /* @__PURE__ */ new Set();
	docWithoutDirectiveSubtrees.definitions.forEach(function(def) {
		if (def.kind === Kind.OPERATION_DEFINITION) populateTransitiveVars(getInUseByOperationName(def.name && def.name.value)).fragmentSpreads.forEach(function(childFragmentName) {
			allFragmentNamesUsed.add(childFragmentName);
		});
		else if (def.kind === Kind.FRAGMENT_DEFINITION && operationCount === 0 && !getInUseByFragmentName(def.name.value).removed) allFragmentNamesUsed.add(def.name.value);
	});
	allFragmentNamesUsed.forEach(function(fragmentName) {
		populateTransitiveVars(getInUseByFragmentName(fragmentName)).fragmentSpreads.forEach(function(childFragmentName) {
			allFragmentNamesUsed.add(childFragmentName);
		});
	});
	var fragmentWillBeRemoved = function(fragmentName) {
		return !!(!allFragmentNamesUsed.has(fragmentName) || getInUseByFragmentName(fragmentName).removed);
	};
	var enterVisitor = { enter: function(node) {
		if (fragmentWillBeRemoved(node.name.value)) return null;
	} };
	return nullIfDocIsEmpty(visit(docWithoutDirectiveSubtrees, {
		FragmentSpread: enterVisitor,
		FragmentDefinition: enterVisitor,
		OperationDefinition: { leave: function(node) {
			if (node.variableDefinitions) {
				var usedVariableNames_1 = populateTransitiveVars(getInUseByOperationName(node.name && node.name.value)).transitiveVars;
				if (usedVariableNames_1.size < node.variableDefinitions.length) return __assign(__assign({}, node), { variableDefinitions: node.variableDefinitions.filter(function(varDef) {
					return usedVariableNames_1.has(varDef.variable.name.value);
				}) });
			}
		} }
	}));
}
var addTypenameToDocument = Object.assign(function(doc) {
	return visit(doc, { SelectionSet: { enter: function(node, _key, parent) {
		if (parent && parent.kind === Kind.OPERATION_DEFINITION) return;
		var selections = node.selections;
		if (!selections) return;
		if (selections.some(function(selection) {
			return isField(selection) && (selection.name.value === "__typename" || selection.name.value.lastIndexOf("__", 0) === 0);
		})) return;
		var field = parent;
		if (isField(field) && field.directives && field.directives.some(function(d) {
			return d.name.value === "export";
		})) return;
		return __assign(__assign({}, node), { selections: __spreadArray(__spreadArray([], selections, true), [TYPENAME_FIELD], false) });
	} } });
}, { added: function(field) {
	return field === TYPENAME_FIELD;
} });
function buildQueryFromSelectionSet(document) {
	if (getMainDefinition(document).operation === "query") return document;
	return visit(document, { OperationDefinition: { enter: function(node) {
		return __assign(__assign({}, node), { operation: "query" });
	} } });
}
function removeClientSetsFromDocument(document) {
	checkDocument(document);
	return removeDirectivesFromDocument([{
		test: function(directive) {
			return directive.name.value === "client";
		},
		remove: true
	}], document);
}
function addNonReactiveToNamedFragments(document) {
	checkDocument(document);
	return visit(document, { FragmentSpread: function(node) {
		var _a;
		if ((_a = node.directives) === null || _a === void 0 ? void 0 : _a.some(function(directive) {
			return directive.name.value === "unmask";
		})) return;
		return __assign(__assign({}, node), { directives: __spreadArray(__spreadArray([], node.directives || [], true), [{
			kind: Kind.DIRECTIVE,
			name: {
				kind: Kind.NAME,
				value: "nonreactive"
			}
		}], false) });
	} });
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/mergeDeep.js
var hasOwnProperty$4 = Object.prototype.hasOwnProperty;
function mergeDeep() {
	var sources = [];
	for (var _i = 0; _i < arguments.length; _i++) sources[_i] = arguments[_i];
	return mergeDeepArray(sources);
}
function mergeDeepArray(sources) {
	var target = sources[0] || {};
	var count = sources.length;
	if (count > 1) {
		var merger = new DeepMerger();
		for (var i = 1; i < count; ++i) target = merger.merge(target, sources[i]);
	}
	return target;
}
var defaultReconciler = function(target, source, property) {
	return this.merge(target[property], source[property]);
};
var DeepMerger = function() {
	function DeepMerger(reconciler) {
		if (reconciler === void 0) reconciler = defaultReconciler;
		this.reconciler = reconciler;
		this.isObject = isNonNullObject;
		this.pastCopies = /* @__PURE__ */ new Set();
	}
	DeepMerger.prototype.merge = function(target, source) {
		var _this = this;
		var context = [];
		for (var _i = 2; _i < arguments.length; _i++) context[_i - 2] = arguments[_i];
		if (isNonNullObject(source) && isNonNullObject(target)) {
			Object.keys(source).forEach(function(sourceKey) {
				if (hasOwnProperty$4.call(target, sourceKey)) {
					var targetValue = target[sourceKey];
					if (source[sourceKey] !== targetValue) {
						var result = _this.reconciler.apply(_this, __spreadArray([
							target,
							source,
							sourceKey
						], context, false));
						if (result !== targetValue) {
							target = _this.shallowCopyForMerge(target);
							target[sourceKey] = result;
						}
					}
				} else {
					target = _this.shallowCopyForMerge(target);
					target[sourceKey] = source[sourceKey];
				}
			});
			return target;
		}
		return source;
	};
	DeepMerger.prototype.shallowCopyForMerge = function(value) {
		if (isNonNullObject(value)) {
			if (!this.pastCopies.has(value)) {
				if (Array.isArray(value)) value = value.slice(0);
				else value = __assign({ __proto__: Object.getPrototypeOf(value) }, value);
				this.pastCopies.add(value);
			}
		}
		return value;
	};
	return DeepMerger;
}();
//#endregion
//#region node_modules/zen-observable-ts/module.js
function _createForOfIteratorHelperLoose(o, allowArrayLike) {
	var it = typeof Symbol !== "undefined" && o[Symbol.iterator] || o["@@iterator"];
	if (it) return (it = it.call(o)).next.bind(it);
	if (Array.isArray(o) || (it = _unsupportedIterableToArray(o)) || allowArrayLike && o && typeof o.length === "number") {
		if (it) o = it;
		var i = 0;
		return function() {
			if (i >= o.length) return { done: true };
			return {
				done: false,
				value: o[i++]
			};
		};
	}
	throw new TypeError("Invalid attempt to iterate non-iterable instance.\nIn order to be iterable, non-array objects must have a [Symbol.iterator]() method.");
}
function _unsupportedIterableToArray(o, minLen) {
	if (!o) return;
	if (typeof o === "string") return _arrayLikeToArray(o, minLen);
	var n = Object.prototype.toString.call(o).slice(8, -1);
	if (n === "Object" && o.constructor) n = o.constructor.name;
	if (n === "Map" || n === "Set") return Array.from(o);
	if (n === "Arguments" || /^(?:Ui|I)nt(?:8|16|32)(?:Clamped)?Array$/.test(n)) return _arrayLikeToArray(o, minLen);
}
function _arrayLikeToArray(arr, len) {
	if (len == null || len > arr.length) len = arr.length;
	for (var i = 0, arr2 = new Array(len); i < len; i++) arr2[i] = arr[i];
	return arr2;
}
function _defineProperties(target, props) {
	for (var i = 0; i < props.length; i++) {
		var descriptor = props[i];
		descriptor.enumerable = descriptor.enumerable || false;
		descriptor.configurable = true;
		if ("value" in descriptor) descriptor.writable = true;
		Object.defineProperty(target, descriptor.key, descriptor);
	}
}
function _createClass(Constructor, protoProps, staticProps) {
	if (protoProps) _defineProperties(Constructor.prototype, protoProps);
	if (staticProps) _defineProperties(Constructor, staticProps);
	Object.defineProperty(Constructor, "prototype", { writable: false });
	return Constructor;
}
var hasSymbols = function() {
	return typeof Symbol === "function";
};
var hasSymbol = function(name) {
	return hasSymbols() && Boolean(Symbol[name]);
};
var getSymbol = function(name) {
	return hasSymbol(name) ? Symbol[name] : "@@" + name;
};
if (hasSymbols() && !hasSymbol("observable")) Symbol.observable = Symbol("observable");
var SymbolIterator = getSymbol("iterator");
var SymbolObservable = getSymbol("observable");
var SymbolSpecies = getSymbol("species");
function getMethod(obj, key) {
	var value = obj[key];
	if (value == null) return void 0;
	if (typeof value !== "function") throw new TypeError(value + " is not a function");
	return value;
}
function getSpecies(obj) {
	var ctor = obj.constructor;
	if (ctor !== void 0) {
		ctor = ctor[SymbolSpecies];
		if (ctor === null) ctor = void 0;
	}
	return ctor !== void 0 ? ctor : Observable;
}
function isObservable(x) {
	return x instanceof Observable;
}
function hostReportError(e) {
	if (hostReportError.log) hostReportError.log(e);
	else setTimeout(function() {
		throw e;
	});
}
function enqueue(fn) {
	Promise.resolve().then(function() {
		try {
			fn();
		} catch (e) {
			hostReportError(e);
		}
	});
}
function cleanupSubscription(subscription) {
	var cleanup = subscription._cleanup;
	if (cleanup === void 0) return;
	subscription._cleanup = void 0;
	if (!cleanup) return;
	try {
		if (typeof cleanup === "function") cleanup();
		else {
			var unsubscribe = getMethod(cleanup, "unsubscribe");
			if (unsubscribe) unsubscribe.call(cleanup);
		}
	} catch (e) {
		hostReportError(e);
	}
}
function closeSubscription(subscription) {
	subscription._observer = void 0;
	subscription._queue = void 0;
	subscription._state = "closed";
}
function flushSubscription(subscription) {
	var queue = subscription._queue;
	if (!queue) return;
	subscription._queue = void 0;
	subscription._state = "ready";
	for (var i = 0; i < queue.length; ++i) {
		notifySubscription(subscription, queue[i].type, queue[i].value);
		if (subscription._state === "closed") break;
	}
}
function notifySubscription(subscription, type, value) {
	subscription._state = "running";
	var observer = subscription._observer;
	try {
		var m = getMethod(observer, type);
		switch (type) {
			case "next":
				if (m) m.call(observer, value);
				break;
			case "error":
				closeSubscription(subscription);
				if (m) m.call(observer, value);
				else throw value;
				break;
			case "complete":
				closeSubscription(subscription);
				if (m) m.call(observer);
				break;
		}
	} catch (e) {
		hostReportError(e);
	}
	if (subscription._state === "closed") cleanupSubscription(subscription);
	else if (subscription._state === "running") subscription._state = "ready";
}
function onNotify(subscription, type, value) {
	if (subscription._state === "closed") return;
	if (subscription._state === "buffering") {
		subscription._queue.push({
			type,
			value
		});
		return;
	}
	if (subscription._state !== "ready") {
		subscription._state = "buffering";
		subscription._queue = [{
			type,
			value
		}];
		enqueue(function() {
			return flushSubscription(subscription);
		});
		return;
	}
	notifySubscription(subscription, type, value);
}
var Subscription = /*#__PURE__*/ function() {
	function Subscription(observer, subscriber) {
		this._cleanup = void 0;
		this._observer = observer;
		this._queue = void 0;
		this._state = "initializing";
		var subscriptionObserver = new SubscriptionObserver(this);
		try {
			this._cleanup = subscriber.call(void 0, subscriptionObserver);
		} catch (e) {
			subscriptionObserver.error(e);
		}
		if (this._state === "initializing") this._state = "ready";
	}
	var _proto = Subscription.prototype;
	_proto.unsubscribe = function unsubscribe() {
		if (this._state !== "closed") {
			closeSubscription(this);
			cleanupSubscription(this);
		}
	};
	_createClass(Subscription, [{
		key: "closed",
		get: function() {
			return this._state === "closed";
		}
	}]);
	return Subscription;
}();
var SubscriptionObserver = /*#__PURE__*/ function() {
	function SubscriptionObserver(subscription) {
		this._subscription = subscription;
	}
	var _proto2 = SubscriptionObserver.prototype;
	_proto2.next = function next(value) {
		onNotify(this._subscription, "next", value);
	};
	_proto2.error = function error(value) {
		onNotify(this._subscription, "error", value);
	};
	_proto2.complete = function complete() {
		onNotify(this._subscription, "complete");
	};
	_createClass(SubscriptionObserver, [{
		key: "closed",
		get: function() {
			return this._subscription._state === "closed";
		}
	}]);
	return SubscriptionObserver;
}();
var Observable = /*#__PURE__*/ function() {
	function Observable(subscriber) {
		if (!(this instanceof Observable)) throw new TypeError("Observable cannot be called as a function");
		if (typeof subscriber !== "function") throw new TypeError("Observable initializer must be a function");
		this._subscriber = subscriber;
	}
	var _proto3 = Observable.prototype;
	_proto3.subscribe = function subscribe(observer) {
		if (typeof observer !== "object" || observer === null) observer = {
			next: observer,
			error: arguments[1],
			complete: arguments[2]
		};
		return new Subscription(observer, this._subscriber);
	};
	_proto3.forEach = function forEach(fn) {
		var _this = this;
		return new Promise(function(resolve, reject) {
			if (typeof fn !== "function") {
				reject(/* @__PURE__ */ new TypeError(fn + " is not a function"));
				return;
			}
			function done() {
				subscription.unsubscribe();
				resolve();
			}
			var subscription = _this.subscribe({
				next: function(value) {
					try {
						fn(value, done);
					} catch (e) {
						reject(e);
						subscription.unsubscribe();
					}
				},
				error: reject,
				complete: resolve
			});
		});
	};
	_proto3.map = function map(fn) {
		var _this2 = this;
		if (typeof fn !== "function") throw new TypeError(fn + " is not a function");
		return new (getSpecies(this))(function(observer) {
			return _this2.subscribe({
				next: function(value) {
					try {
						value = fn(value);
					} catch (e) {
						return observer.error(e);
					}
					observer.next(value);
				},
				error: function(e) {
					observer.error(e);
				},
				complete: function() {
					observer.complete();
				}
			});
		});
	};
	_proto3.filter = function filter(fn) {
		var _this3 = this;
		if (typeof fn !== "function") throw new TypeError(fn + " is not a function");
		return new (getSpecies(this))(function(observer) {
			return _this3.subscribe({
				next: function(value) {
					try {
						if (!fn(value)) return;
					} catch (e) {
						return observer.error(e);
					}
					observer.next(value);
				},
				error: function(e) {
					observer.error(e);
				},
				complete: function() {
					observer.complete();
				}
			});
		});
	};
	_proto3.reduce = function reduce(fn) {
		var _this4 = this;
		if (typeof fn !== "function") throw new TypeError(fn + " is not a function");
		var C = getSpecies(this);
		var hasSeed = arguments.length > 1;
		var hasValue = false;
		var acc = arguments[1];
		return new C(function(observer) {
			return _this4.subscribe({
				next: function(value) {
					var first = !hasValue;
					hasValue = true;
					if (!first || hasSeed) try {
						acc = fn(acc, value);
					} catch (e) {
						return observer.error(e);
					}
					else acc = value;
				},
				error: function(e) {
					observer.error(e);
				},
				complete: function() {
					if (!hasValue && !hasSeed) return observer.error(/* @__PURE__ */ new TypeError("Cannot reduce an empty sequence"));
					observer.next(acc);
					observer.complete();
				}
			});
		});
	};
	_proto3.concat = function concat() {
		var _this5 = this;
		for (var _len = arguments.length, sources = new Array(_len), _key = 0; _key < _len; _key++) sources[_key] = arguments[_key];
		var C = getSpecies(this);
		return new C(function(observer) {
			var subscription;
			var index = 0;
			function startNext(next) {
				subscription = next.subscribe({
					next: function(v) {
						observer.next(v);
					},
					error: function(e) {
						observer.error(e);
					},
					complete: function() {
						if (index === sources.length) {
							subscription = void 0;
							observer.complete();
						} else startNext(C.from(sources[index++]));
					}
				});
			}
			startNext(_this5);
			return function() {
				if (subscription) {
					subscription.unsubscribe();
					subscription = void 0;
				}
			};
		});
	};
	_proto3.flatMap = function flatMap(fn) {
		var _this6 = this;
		if (typeof fn !== "function") throw new TypeError(fn + " is not a function");
		var C = getSpecies(this);
		return new C(function(observer) {
			var subscriptions = [];
			var outer = _this6.subscribe({
				next: function(value) {
					if (fn) try {
						value = fn(value);
					} catch (e) {
						return observer.error(e);
					}
					var inner = C.from(value).subscribe({
						next: function(value) {
							observer.next(value);
						},
						error: function(e) {
							observer.error(e);
						},
						complete: function() {
							var i = subscriptions.indexOf(inner);
							if (i >= 0) subscriptions.splice(i, 1);
							completeIfDone();
						}
					});
					subscriptions.push(inner);
				},
				error: function(e) {
					observer.error(e);
				},
				complete: function() {
					completeIfDone();
				}
			});
			function completeIfDone() {
				if (outer.closed && subscriptions.length === 0) observer.complete();
			}
			return function() {
				subscriptions.forEach(function(s) {
					return s.unsubscribe();
				});
				outer.unsubscribe();
			};
		});
	};
	_proto3[SymbolObservable] = function() {
		return this;
	};
	Observable.from = function from(x) {
		var C = typeof this === "function" ? this : Observable;
		if (x == null) throw new TypeError(x + " is not an object");
		var method = getMethod(x, SymbolObservable);
		if (method) {
			var observable = method.call(x);
			if (Object(observable) !== observable) throw new TypeError(observable + " is not an object");
			if (isObservable(observable) && observable.constructor === C) return observable;
			return new C(function(observer) {
				return observable.subscribe(observer);
			});
		}
		if (hasSymbol("iterator")) {
			method = getMethod(x, SymbolIterator);
			if (method) return new C(function(observer) {
				enqueue(function() {
					if (observer.closed) return;
					for (var _iterator = _createForOfIteratorHelperLoose(method.call(x)), _step; !(_step = _iterator()).done;) {
						var item = _step.value;
						observer.next(item);
						if (observer.closed) return;
					}
					observer.complete();
				});
			});
		}
		if (Array.isArray(x)) return new C(function(observer) {
			enqueue(function() {
				if (observer.closed) return;
				for (var i = 0; i < x.length; ++i) {
					observer.next(x[i]);
					if (observer.closed) return;
				}
				observer.complete();
			});
		});
		throw new TypeError(x + " is not observable");
	};
	Observable.of = function of() {
		for (var _len2 = arguments.length, items = new Array(_len2), _key2 = 0; _key2 < _len2; _key2++) items[_key2] = arguments[_key2];
		return new (typeof this === "function" ? this : Observable)(function(observer) {
			enqueue(function() {
				if (observer.closed) return;
				for (var i = 0; i < items.length; ++i) {
					observer.next(items[i]);
					if (observer.closed) return;
				}
				observer.complete();
			});
		});
	};
	_createClass(Observable, null, [{
		key: SymbolSpecies,
		get: function() {
			return this;
		}
	}]);
	return Observable;
}();
if (hasSymbols()) Object.defineProperty(Observable, Symbol("extensions"), {
	value: {
		symbol: SymbolObservable,
		hostReportError
	},
	configurable: true
});
//#endregion
//#region node_modules/@apollo/client/utilities/promises/preventUnhandledRejection.js
function preventUnhandledRejection(promise) {
	promise.catch(function() {});
	return promise;
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/cloneDeep.js
var toString$1 = Object.prototype.toString;
/**
* Deeply clones a value to create a new instance.
*/
function cloneDeep(value) {
	return cloneDeepHelper(value);
}
function cloneDeepHelper(val, seen) {
	switch (toString$1.call(val)) {
		case "[object Array]":
			seen = seen || /* @__PURE__ */ new Map();
			if (seen.has(val)) return seen.get(val);
			var copy_1 = val.slice(0);
			seen.set(val, copy_1);
			copy_1.forEach(function(child, i) {
				copy_1[i] = cloneDeepHelper(child, seen);
			});
			return copy_1;
		case "[object Object]":
			seen = seen || /* @__PURE__ */ new Map();
			if (seen.has(val)) return seen.get(val);
			var copy_2 = Object.create(Object.getPrototypeOf(val));
			seen.set(val, copy_2);
			Object.keys(val).forEach(function(key) {
				copy_2[key] = cloneDeepHelper(val[key], seen);
			});
			return copy_2;
		default: return val;
	}
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/maybeDeepFreeze.js
function deepFreeze(value) {
	var workSet = new Set([value]);
	workSet.forEach(function(obj) {
		if (isNonNullObject(obj) && shallowFreeze(obj) === obj) Object.getOwnPropertyNames(obj).forEach(function(name) {
			if (isNonNullObject(obj[name])) workSet.add(obj[name]);
		});
	});
	return value;
}
function shallowFreeze(obj) {
	if (globalThis.__DEV__ !== false && !Object.isFrozen(obj)) try {
		Object.freeze(obj);
	} catch (e) {
		if (e instanceof TypeError) return null;
		throw e;
	}
	return obj;
}
function maybeDeepFreeze(obj) {
	if (globalThis.__DEV__ !== false) deepFreeze(obj);
	return obj;
}
//#endregion
//#region node_modules/@apollo/client/utilities/observables/iteration.js
/**
* @deprecated `iterateObserversSafely` will be removed with Apollo Client 4.0.
* Please discontinue using this function.
*/
function iterateObserversSafely(observers, method, argument) {
	var observersWithMethod = [];
	observers.forEach(function(obs) {
		return obs[method] && observersWithMethod.push(obs);
	});
	observersWithMethod.forEach(function(obs) {
		return obs[method](argument);
	});
}
//#endregion
//#region node_modules/@apollo/client/utilities/observables/asyncMap.js
/**
* @deprecated `asyncMap` will be removed in Apollo Client 4.0. This function is
* safe to use in Apollo Client 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When migrating**
*
* Prefer to use RxJS's built in helpers. Convert promises into observables
* using the [`from`](https://rxjs.dev/api/index/function/from) function.
*/
function asyncMap(observable, mapFn, catchFn) {
	return new Observable(function(observer) {
		var promiseQueue = { then: function(callback) {
			return new Promise(function(resolve) {
				return resolve(callback());
			});
		} };
		function makeCallback(examiner, key) {
			return function(arg) {
				if (examiner) {
					var both = function() {
						return observer.closed ? 0 : examiner(arg);
					};
					promiseQueue = promiseQueue.then(both, both).then(function(result) {
						return observer.next(result);
					}, function(error) {
						return observer.error(error);
					});
				} else observer[key](arg);
			};
		}
		var handler = {
			next: makeCallback(mapFn, "next"),
			error: makeCallback(catchFn, "error"),
			complete: function() {
				promiseQueue.then(function() {
					return observer.complete();
				});
			}
		};
		var sub = observable.subscribe(handler);
		return function() {
			return sub.unsubscribe();
		};
	});
}
//#endregion
//#region node_modules/@apollo/client/utilities/observables/subclassing.js
function fixObservableSubclass(subclass) {
	function set(key) {
		Object.defineProperty(subclass, key, { value: Observable });
	}
	if (canUseSymbol && Symbol.species) set(Symbol.species);
	set("@@species");
	return subclass;
}
//#endregion
//#region node_modules/@apollo/client/utilities/observables/Concast.js
function isPromiseLike(value) {
	return value && typeof value.then === "function";
}
var Concast = function(_super) {
	__extends(Concast, _super);
	function Concast(sources) {
		var _this = _super.call(this, function(observer) {
			_this.addObserver(observer);
			return function() {
				return _this.removeObserver(observer);
			};
		}) || this;
		_this.observers = /* @__PURE__ */ new Set();
		_this.promise = new Promise(function(resolve, reject) {
			_this.resolve = resolve;
			_this.reject = reject;
		});
		_this.handlers = {
			next: function(result) {
				if (_this.sub !== null) {
					_this.latest = ["next", result];
					_this.notify("next", result);
					iterateObserversSafely(_this.observers, "next", result);
				}
			},
			error: function(error) {
				var sub = _this.sub;
				if (sub !== null) {
					if (sub) setTimeout(function() {
						return sub.unsubscribe();
					});
					_this.sub = null;
					_this.latest = ["error", error];
					_this.reject(error);
					_this.notify("error", error);
					iterateObserversSafely(_this.observers, "error", error);
				}
			},
			complete: function() {
				var _a = _this, sub = _a.sub, _b = _a.sources, sources = _b === void 0 ? [] : _b;
				if (sub !== null) {
					var value = sources.shift();
					if (!value) {
						if (sub) setTimeout(function() {
							return sub.unsubscribe();
						});
						_this.sub = null;
						if (_this.latest && _this.latest[0] === "next") _this.resolve(_this.latest[1]);
						else _this.resolve();
						_this.notify("complete");
						iterateObserversSafely(_this.observers, "complete");
					} else if (isPromiseLike(value)) value.then(function(obs) {
						return _this.sub = obs.subscribe(_this.handlers);
					}, _this.handlers.error);
					else _this.sub = value.subscribe(_this.handlers);
				}
			}
		};
		_this.nextResultListeners = /* @__PURE__ */ new Set();
		_this.cancel = function(reason) {
			_this.reject(reason);
			_this.sources = [];
			_this.handlers.error(reason);
		};
		_this.promise.catch(function(_) {});
		if (typeof sources === "function") sources = [new Observable(sources)];
		if (isPromiseLike(sources)) sources.then(function(iterable) {
			return _this.start(iterable);
		}, _this.handlers.error);
		else _this.start(sources);
		return _this;
	}
	Concast.prototype.start = function(sources) {
		if (this.sub !== void 0) return;
		this.sources = Array.from(sources);
		this.handlers.complete();
	};
	Concast.prototype.deliverLastMessage = function(observer) {
		if (this.latest) {
			var nextOrError = this.latest[0];
			var method = observer[nextOrError];
			if (method) method.call(observer, this.latest[1]);
			if (this.sub === null && nextOrError === "next" && observer.complete) observer.complete();
		}
	};
	Concast.prototype.addObserver = function(observer) {
		if (!this.observers.has(observer)) {
			this.deliverLastMessage(observer);
			this.observers.add(observer);
		}
	};
	Concast.prototype.removeObserver = function(observer) {
		if (this.observers.delete(observer) && this.observers.size < 1) this.handlers.complete();
	};
	Concast.prototype.notify = function(method, arg) {
		var nextResultListeners = this.nextResultListeners;
		if (nextResultListeners.size) {
			this.nextResultListeners = /* @__PURE__ */ new Set();
			nextResultListeners.forEach(function(listener) {
				return listener(method, arg);
			});
		}
	};
	Concast.prototype.beforeNext = function(callback) {
		var called = false;
		this.nextResultListeners.add(function(method, arg) {
			if (!called) {
				called = true;
				callback(method, arg);
			}
		});
	};
	return Concast;
}(Observable);
fixObservableSubclass(Concast);
//#endregion
//#region node_modules/@apollo/client/utilities/common/incrementalResult.js
function isExecutionPatchIncrementalResult(value) {
	return "incremental" in value;
}
function isExecutionPatchInitialResult(value) {
	return "hasNext" in value && "data" in value;
}
function isExecutionPatchResult(value) {
	return isExecutionPatchIncrementalResult(value) || isExecutionPatchInitialResult(value);
}
function isApolloPayloadResult(value) {
	return isNonNullObject(value) && "payload" in value;
}
function mergeIncrementalData(prevResult, result) {
	var mergedData = prevResult;
	var merger = new DeepMerger();
	if (isExecutionPatchIncrementalResult(result) && isNonEmptyArray(result.incremental)) result.incremental.forEach(function(_a) {
		var data = _a.data, path = _a.path;
		for (var i = path.length - 1; i >= 0; --i) {
			var key = path[i];
			var parent_1 = !isNaN(+key) ? [] : {};
			parent_1[key] = data;
			data = parent_1;
		}
		mergedData = merger.merge(mergedData, data);
	});
	return mergedData;
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/errorHandling.js
function graphQLResultHasError(result) {
	return isNonEmptyArray(getGraphQLErrorsFromResult(result));
}
function getGraphQLErrorsFromResult(result) {
	var graphQLErrors = isNonEmptyArray(result.errors) ? result.errors.slice(0) : [];
	if (isExecutionPatchIncrementalResult(result) && isNonEmptyArray(result.incremental)) result.incremental.forEach(function(incrementalResult) {
		if (incrementalResult.errors) graphQLErrors.push.apply(graphQLErrors, incrementalResult.errors);
	});
	return graphQLErrors;
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/compact.js
/**
* Merges the provided objects shallowly and removes
* all properties with an `undefined` value
*/
function compact() {
	var objects = [];
	for (var _i = 0; _i < arguments.length; _i++) objects[_i] = arguments[_i];
	var result = Object.create(null);
	objects.forEach(function(obj) {
		if (!obj) return;
		Object.keys(obj).forEach(function(key) {
			var value = obj[key];
			if (value !== void 0) result[key] = value;
		});
	});
	return result;
}
//#endregion
//#region node_modules/@apollo/client/utilities/common/mergeOptions.js
function mergeOptions(defaults, options) {
	return compact(defaults, options, options.variables && { variables: compact(__assign(__assign({}, defaults && defaults.variables), options.variables)) });
}
//#endregion
//#region node_modules/@apollo/client/link/utils/fromError.js
/**
* @deprecated `fromError` will be removed in Apollo Client 4.0. This is safe
* to use in 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When upgrading**
*
* Use RxJS's [`throwError`](https://rxjs.dev/api/index/function/throwError) function.
*
* ```ts
* const observable = throwError(() => new Error(...));
* ```
*/
function fromError(errorValue) {
	return new Observable(function(observer) {
		observer.error(errorValue);
	});
}
//#endregion
//#region node_modules/@apollo/client/link/utils/toPromise.js
/**
* @deprecated `toPromise` will be removed in Apollo Client 4.0. This is safe
* to use in 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When upgrading**
*
* Use RxJS's [`firstValueFrom`](https://rxjs.dev/api/index/function/firstValueFrom) function.
*
* ```ts
* const result = await firstValueFrom(observable);
* ```
*/
function toPromise(observable) {
	var completed = false;
	return new Promise(function(resolve, reject) {
		observable.subscribe({
			next: function(data) {
				if (completed) globalThis.__DEV__ !== false && invariant$1.warn(57);
				else {
					completed = true;
					resolve(data);
				}
			},
			error: reject
		});
	});
}
//#endregion
//#region node_modules/@apollo/client/link/utils/fromPromise.js
/**
* @deprecated `fromPromise` will be removed in Apollo Client 4.0. This is safe
* to use in 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When upgrading**
*
* Use RxJS's [`from`](https://rxjs.dev/api/index/function/from) function.
*
* ```ts
* const observable = from(promise);
* ```
*/
function fromPromise(promise) {
	return new Observable(function(observer) {
		promise.then(function(value) {
			observer.next(value);
			observer.complete();
		}).catch(observer.error.bind(observer));
	});
}
//#endregion
//#region node_modules/@apollo/client/link/utils/throwServerError.js
/**
* @deprecated `throwServerError` will be removed in Apollo Client 4.0. This is
* safe to use in Apollo Client 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When migrating**
*
* `ServerError` is a subclass of `Error`. To throw a server error, use
* `throw new ServerError(...)` instead.
*
* ```ts
* throw new ServerError("error message", { response, result });
* ```
*/
var throwServerError = function(response, result, message) {
	var error = new Error(message);
	error.name = "ServerError";
	error.response = response;
	error.statusCode = response.status;
	error.result = result;
	throw error;
};
//#endregion
//#region node_modules/@apollo/client/link/utils/validateOperation.js
function validateOperation(operation) {
	var OPERATION_FIELDS = [
		"query",
		"operationName",
		"variables",
		"extensions",
		"context"
	];
	for (var _i = 0, _a = Object.keys(operation); _i < _a.length; _i++) {
		var key = _a[_i];
		if (OPERATION_FIELDS.indexOf(key) < 0) throw newInvariantError(58, key);
	}
	return operation;
}
//#endregion
//#region node_modules/@apollo/client/link/utils/createOperation.js
function createOperation(starting, operation) {
	var context = __assign({}, starting);
	var setContext = function(next) {
		if (typeof next === "function") context = __assign(__assign({}, context), next(context));
		else context = __assign(__assign({}, context), next);
	};
	var getContext = function() {
		return __assign({}, context);
	};
	Object.defineProperty(operation, "setContext", {
		enumerable: false,
		value: setContext
	});
	Object.defineProperty(operation, "getContext", {
		enumerable: false,
		value: getContext
	});
	return operation;
}
//#endregion
//#region node_modules/@apollo/client/link/utils/transformOperation.js
function transformOperation(operation) {
	var transformedOperation = {
		variables: operation.variables || {},
		extensions: operation.extensions || {},
		operationName: operation.operationName,
		query: operation.query
	};
	if (!transformedOperation.operationName) transformedOperation.operationName = typeof transformedOperation.query !== "string" ? getOperationName(transformedOperation.query) || void 0 : "";
	return transformedOperation;
}
//#endregion
//#region node_modules/@apollo/client/link/utils/filterOperationVariables.js
function filterOperationVariables(variables, query) {
	var result = __assign({}, variables);
	var unusedNames = new Set(Object.keys(variables));
	visit(query, { Variable: function(node, _key, parent) {
		if (parent && parent.kind !== "VariableDefinition") unusedNames.delete(node.name.value);
	} });
	unusedNames.forEach(function(name) {
		delete result[name];
	});
	return result;
}
//#endregion
//#region node_modules/@apollo/client/utilities/deprecation/index.js
var muteAllDeprecations = Symbol.for("apollo.deprecations");
var global$1 = global_default;
var slot = new Slot();
function isMuted(name) {
	return global$1[muteAllDeprecations] || (slot.getValue() || []).includes(name);
}
function muteDeprecations(name) {
	var args = [];
	for (var _i = 1; _i < arguments.length; _i++) args[_i - 1] = arguments[_i];
	return slot.withValue.apply(slot, __spreadArray([Array.isArray(name) ? name : [name]], args, false));
}
function warnRemovedOption(options, name, callSite, recommendation) {
	if (recommendation === void 0) recommendation = "Please remove this option.";
	warnDeprecated(name, function() {
		if (name in options) globalThis.__DEV__ !== false && invariant$1.warn(104, callSite, name, recommendation);
	});
}
function warnDeprecated(name, cb) {
	if (!isMuted(name)) cb();
}
//#endregion
//#region node_modules/@apollo/client/link/core/ApolloLink.js
function passthrough(op, forward) {
	return forward ? forward(op) : Observable.of();
}
function toLink(handler) {
	return typeof handler === "function" ? new ApolloLink(handler) : handler;
}
function isTerminating(link) {
	return link.request.length <= 1;
}
var ApolloLink = function() {
	function ApolloLink(request) {
		if (request) this.request = request;
	}
	ApolloLink.empty = function() {
		return new ApolloLink(function() {
			return Observable.of();
		});
	};
	ApolloLink.from = function(links) {
		if (links.length === 0) return ApolloLink.empty();
		return links.map(toLink).reduce(function(x, y) {
			return x.concat(y);
		});
	};
	ApolloLink.split = function(test, left, right) {
		var leftLink = toLink(left);
		var rightLink = toLink(right || new ApolloLink(passthrough));
		var ret;
		if (isTerminating(leftLink) && isTerminating(rightLink)) ret = new ApolloLink(function(operation) {
			return test(operation) ? leftLink.request(operation) || Observable.of() : rightLink.request(operation) || Observable.of();
		});
		else ret = new ApolloLink(function(operation, forward) {
			return test(operation) ? leftLink.request(operation, forward) || Observable.of() : rightLink.request(operation, forward) || Observable.of();
		});
		return Object.assign(ret, {
			left: leftLink,
			right: rightLink
		});
	};
	ApolloLink.execute = function(link, operation) {
		return link.request(createOperation(operation.context, transformOperation(validateOperation(operation)))) || Observable.of();
	};
	ApolloLink.concat = function(first, second) {
		var firstLink = toLink(first);
		if (isTerminating(firstLink)) {
			globalThis.__DEV__ !== false && invariant$1.warn(47, firstLink);
			return firstLink;
		}
		var nextLink = toLink(second);
		var ret;
		if (isTerminating(nextLink)) ret = new ApolloLink(function(operation) {
			return firstLink.request(operation, function(op) {
				return nextLink.request(op) || Observable.of();
			}) || Observable.of();
		});
		else ret = new ApolloLink(function(operation, forward) {
			return firstLink.request(operation, function(op) {
				return nextLink.request(op, forward) || Observable.of();
			}) || Observable.of();
		});
		return Object.assign(ret, {
			left: firstLink,
			right: nextLink
		});
	};
	ApolloLink.prototype.split = function(test, left, right) {
		return this.concat(ApolloLink.split(test, left, right || new ApolloLink(passthrough)));
	};
	ApolloLink.prototype.concat = function(next) {
		return ApolloLink.concat(this, next);
	};
	ApolloLink.prototype.request = function(operation, forward) {
		throw newInvariantError(48);
	};
	/**
	* @deprecated `onError` will be removed with Apollo Client 4.0. Please
	* discontinue using this method.
	*/
	ApolloLink.prototype.onError = function(error, observer) {
		if (globalThis.__DEV__ !== false) warnDeprecated("onError", function() {
			globalThis.__DEV__ !== false && invariant$1.warn(49);
		});
		if (observer && observer.error) {
			observer.error(error);
			return false;
		}
		throw error;
	};
	/**
	* @deprecated `setOnError` will be removed with Apollo Client 4.0. Please
	* discontinue using this method.
	*/
	ApolloLink.prototype.setOnError = function(fn) {
		if (globalThis.__DEV__ !== false) globalThis.__DEV__ !== false && invariant$1.warn(50);
		this.onError = fn;
		return this;
	};
	return ApolloLink;
}();
//#endregion
//#region node_modules/@apollo/client/link/core/empty.js
var empty = ApolloLink.empty;
//#endregion
//#region node_modules/@apollo/client/link/core/from.js
var from = ApolloLink.from;
//#endregion
//#region node_modules/@apollo/client/link/core/split.js
var split = ApolloLink.split;
//#endregion
//#region node_modules/@apollo/client/link/core/concat.js
var concat = ApolloLink.concat;
//#endregion
//#region node_modules/@apollo/client/link/core/execute.js
var execute = ApolloLink.execute;
//#endregion
//#region node_modules/@apollo/client/link/http/iterators/async.js
/**
* Original source:
* https://github.com/kmalakoff/response-iterator/blob/master/src/iterators/async.ts
*/
function asyncIterator(source) {
	var _a;
	var iterator = source[Symbol.asyncIterator]();
	return _a = { next: function() {
		return iterator.next();
	} }, _a[Symbol.asyncIterator] = function() {
		return this;
	}, _a;
}
//#endregion
//#region node_modules/@apollo/client/link/http/iterators/nodeStream.js
/**
* Original source:
* https://github.com/kmalakoff/response-iterator/blob/master/src/iterators/nodeStream.ts
*/
function nodeStreamIterator(stream) {
	var cleanup = null;
	var error = null;
	var done = false;
	var data = [];
	var waiting = [];
	function onData(chunk) {
		if (error) return;
		if (waiting.length) {
			var shiftedArr = waiting.shift();
			if (Array.isArray(shiftedArr) && shiftedArr[0]) return shiftedArr[0]({
				value: chunk,
				done: false
			});
		}
		data.push(chunk);
	}
	function onError(err) {
		error = err;
		waiting.slice().forEach(function(pair) {
			pair[1](err);
		});
		!cleanup || cleanup();
	}
	function onEnd() {
		done = true;
		waiting.slice().forEach(function(pair) {
			pair[0]({
				value: void 0,
				done: true
			});
		});
		!cleanup || cleanup();
	}
	cleanup = function() {
		cleanup = null;
		stream.removeListener("data", onData);
		stream.removeListener("error", onError);
		stream.removeListener("end", onEnd);
		stream.removeListener("finish", onEnd);
		stream.removeListener("close", onEnd);
	};
	stream.on("data", onData);
	stream.on("error", onError);
	stream.on("end", onEnd);
	stream.on("finish", onEnd);
	stream.on("close", onEnd);
	function getNext() {
		return new Promise(function(resolve, reject) {
			if (error) return reject(error);
			if (data.length) return resolve({
				value: data.shift(),
				done: false
			});
			if (done) return resolve({
				value: void 0,
				done: true
			});
			waiting.push([resolve, reject]);
		});
	}
	var iterator = { next: function() {
		return getNext();
	} };
	if (canUseAsyncIteratorSymbol) iterator[Symbol.asyncIterator] = function() {
		return this;
	};
	return iterator;
}
//#endregion
//#region node_modules/@apollo/client/link/http/iterators/promise.js
/**
* Original source:
* https://github.com/kmalakoff/response-iterator/blob/master/src/iterators/promise.ts
*/
function promiseIterator(promise) {
	var resolved = false;
	var iterator = { next: function() {
		if (resolved) return Promise.resolve({
			value: void 0,
			done: true
		});
		resolved = true;
		return new Promise(function(resolve, reject) {
			promise.then(function(value) {
				resolve({
					value,
					done: false
				});
			}).catch(reject);
		});
	} };
	if (canUseAsyncIteratorSymbol) iterator[Symbol.asyncIterator] = function() {
		return this;
	};
	return iterator;
}
//#endregion
//#region node_modules/@apollo/client/link/http/iterators/reader.js
/**
* Original source:
* https://github.com/kmalakoff/response-iterator/blob/master/src/iterators/reader.ts
*/
function readerIterator(reader) {
	var iterator = { next: function() {
		return reader.read();
	} };
	if (canUseAsyncIteratorSymbol) iterator[Symbol.asyncIterator] = function() {
		return this;
	};
	return iterator;
}
//#endregion
//#region node_modules/@apollo/client/link/http/responseIterator.js
/**
* Original source:
* https://github.com/kmalakoff/response-iterator/blob/master/src/index.ts
*/
function isNodeResponse(value) {
	return !!value.body;
}
function isReadableStream(value) {
	return !!value.getReader;
}
function isAsyncIterableIterator(value) {
	return !!(canUseAsyncIteratorSymbol && value[Symbol.asyncIterator]);
}
function isStreamableBlob(value) {
	return !!value.stream;
}
function isBlob(value) {
	return !!value.arrayBuffer;
}
function isNodeReadableStream(value) {
	return !!value.pipe;
}
function responseIterator(response) {
	var body = response;
	if (isNodeResponse(response)) body = response.body;
	if (isAsyncIterableIterator(body)) return asyncIterator(body);
	if (isReadableStream(body)) return readerIterator(body.getReader());
	if (isStreamableBlob(body)) return readerIterator(body.stream().getReader());
	if (isBlob(body)) return promiseIterator(body.arrayBuffer());
	if (isNodeReadableStream(body)) return nodeStreamIterator(body);
	throw new Error("Unknown body type for responseIterator. Please pass a streamable response.");
}
//#endregion
//#region node_modules/@apollo/client/errors/index.js
var PROTOCOL_ERRORS_SYMBOL = Symbol();
function graphQLResultHasProtocolErrors(result) {
	if (result.extensions) return Array.isArray(result.extensions[PROTOCOL_ERRORS_SYMBOL]);
	return false;
}
/**
* @deprecated `isApolloError` will be removed with Apollo Client 4.0. This
* function is safe to use in Apollo Client 3.x.
*
* **Recommended now**
*
* No action needed
*
* **When migrating**
*
* Errors are no longer wrapped in Apollo Client 4.0. To check if an error is an
* instance of an error provided by Apollo Client, use the static `.is` method
* on the error class you want to test against.
*
* ```ts
* // Test if an error is an instance of `CombinedGraphQLErrors`
* const isGraphQLErrors = CombinedGraphQLErrors.is(error);
* ```
*/
function isApolloError(err) {
	return err.hasOwnProperty("graphQLErrors");
}
var generateErrorMessage = function(err) {
	var errors = __spreadArray(__spreadArray(__spreadArray([], err.graphQLErrors, true), err.clientErrors, true), err.protocolErrors, true);
	if (err.networkError) errors.push(err.networkError);
	return errors.map(function(err) {
		return isNonNullObject(err) && err.message || "Error message not found.";
	}).join("\n");
};
var ApolloError = function(_super) {
	__extends(ApolloError, _super);
	function ApolloError(_a) {
		var graphQLErrors = _a.graphQLErrors, protocolErrors = _a.protocolErrors, clientErrors = _a.clientErrors, networkError = _a.networkError, errorMessage = _a.errorMessage, extraInfo = _a.extraInfo;
		var _this = _super.call(this, errorMessage) || this;
		_this.name = "ApolloError";
		_this.graphQLErrors = graphQLErrors || [];
		_this.protocolErrors = protocolErrors || [];
		_this.clientErrors = clientErrors || [];
		_this.networkError = networkError || null;
		_this.message = errorMessage || generateErrorMessage(_this);
		_this.extraInfo = extraInfo;
		_this.cause = __spreadArray(__spreadArray(__spreadArray([networkError], graphQLErrors || [], true), protocolErrors || [], true), clientErrors || [], true).find(function(e) {
			return !!e;
		}) || null;
		_this.__proto__ = ApolloError.prototype;
		return _this;
	}
	return ApolloError;
}(Error);
//#endregion
//#region node_modules/@apollo/client/link/http/parseAndCheckHttpResponse.js
var hasOwnProperty$3 = Object.prototype.hasOwnProperty;
function readMultipartBody(response, nextValue) {
	return __awaiter(this, void 0, void 0, function() {
		var decoder, contentType, delimiter, boundaryVal, boundary, buffer, iterator, running, _a, value, done, chunk, searchFrom, bi, message, i, headers, contentType_1, body, result, next;
		var _b, _c;
		var _d;
		return __generator(this, function(_e) {
			switch (_e.label) {
				case 0:
					if (TextDecoder === void 0) throw new Error("TextDecoder must be defined in the environment: please import a polyfill.");
					decoder = new TextDecoder("utf-8");
					contentType = (_d = response.headers) === null || _d === void 0 ? void 0 : _d.get("content-type");
					delimiter = "boundary=";
					boundaryVal = (contentType === null || contentType === void 0 ? void 0 : contentType.includes(delimiter)) ? contentType === null || contentType === void 0 ? void 0 : contentType.substring((contentType === null || contentType === void 0 ? void 0 : contentType.indexOf(delimiter)) + delimiter.length).replace(/['"]/g, "").replace(/\;(.*)/gm, "").trim() : "-";
					boundary = "\r\n--".concat(boundaryVal);
					buffer = "";
					iterator = responseIterator(response);
					running = true;
					_e.label = 1;
				case 1:
					if (!running) return [3, 3];
					return [4, iterator.next()];
				case 2:
					_a = _e.sent(), value = _a.value, done = _a.done;
					chunk = typeof value === "string" ? value : decoder.decode(value);
					searchFrom = buffer.length - boundary.length + 1;
					running = !done;
					buffer += chunk;
					bi = buffer.indexOf(boundary, searchFrom);
					while (bi > -1) {
						message = void 0;
						_b = [buffer.slice(0, bi), buffer.slice(bi + boundary.length)], message = _b[0], buffer = _b[1];
						i = message.indexOf("\r\n\r\n");
						headers = parseHeaders(message.slice(0, i));
						contentType_1 = headers["content-type"];
						if (contentType_1 && contentType_1.toLowerCase().indexOf("application/json") === -1) throw new Error("Unsupported patch content type: application/json is required.");
						body = message.slice(i);
						if (body) {
							result = parseJsonBody(response, body);
							if (Object.keys(result).length > 1 || "data" in result || "incremental" in result || "errors" in result || "payload" in result) if (isApolloPayloadResult(result)) {
								next = {};
								if ("payload" in result) {
									if (Object.keys(result).length === 1 && result.payload === null) return [2];
									next = __assign({}, result.payload);
								}
								if ("errors" in result) next = __assign(__assign({}, next), { extensions: __assign(__assign({}, "extensions" in next ? next.extensions : null), (_c = {}, _c[PROTOCOL_ERRORS_SYMBOL] = result.errors, _c)) });
								nextValue(next);
							} else nextValue(result);
							else if (Object.keys(result).length === 1 && "hasNext" in result && !result.hasNext) return [2];
						}
						bi = buffer.indexOf(boundary);
					}
					return [3, 1];
				case 3: return [2];
			}
		});
	});
}
function parseHeaders(headerText) {
	var headersInit = {};
	headerText.split("\n").forEach(function(line) {
		var i = line.indexOf(":");
		if (i > -1) {
			var name_1 = line.slice(0, i).trim().toLowerCase();
			headersInit[name_1] = line.slice(i + 1).trim();
		}
	});
	return headersInit;
}
function parseJsonBody(response, bodyText) {
	if (response.status >= 300) {
		var getResult = function() {
			try {
				return JSON.parse(bodyText);
			} catch (err) {
				return bodyText;
			}
		};
		throwServerError(response, getResult(), "Response not successful: Received status code ".concat(response.status));
	}
	try {
		return JSON.parse(bodyText);
	} catch (err) {
		var parseError = err;
		parseError.name = "ServerParseError";
		parseError.response = response;
		parseError.statusCode = response.status;
		parseError.bodyText = bodyText;
		throw parseError;
	}
}
function handleError(err, observer) {
	if (err.result && err.result.errors && err.result.data) observer.next(err.result);
	observer.error(err);
}
function parseAndCheckHttpResponse(operations) {
	return function(response) {
		return response.text().then(function(bodyText) {
			return parseJsonBody(response, bodyText);
		}).then(function(result) {
			if (!Array.isArray(result) && !hasOwnProperty$3.call(result, "data") && !hasOwnProperty$3.call(result, "errors")) throwServerError(response, result, "Server response was missing for query '".concat(Array.isArray(operations) ? operations.map(function(op) {
				return op.operationName;
			}) : operations.operationName, "'."));
			return result;
		});
	};
}
//#endregion
//#region node_modules/@apollo/client/link/http/serializeFetchParameter.js
var serializeFetchParameter = function(p, label) {
	var serialized;
	try {
		serialized = JSON.stringify(p);
	} catch (e) {
		var parseError = newInvariantError(54, label, e.message);
		parseError.parseError = e;
		throw parseError;
	}
	return serialized;
};
var fallbackHttpConfig = {
	http: {
		includeQuery: true,
		includeExtensions: false,
		preserveHeaderCase: false
	},
	headers: {
		accept: "*/*",
		"content-type": "application/json"
	},
	options: { method: "POST" }
};
var defaultPrinter = function(ast, printer) {
	return printer(ast);
};
function selectHttpOptionsAndBody(operation, fallbackConfig) {
	var configs = [];
	for (var _i = 2; _i < arguments.length; _i++) configs[_i - 2] = arguments[_i];
	configs.unshift(fallbackConfig);
	return selectHttpOptionsAndBodyInternal.apply(void 0, __spreadArray([operation, defaultPrinter], configs, false));
}
function selectHttpOptionsAndBodyInternal(operation, printer) {
	var configs = [];
	for (var _i = 2; _i < arguments.length; _i++) configs[_i - 2] = arguments[_i];
	var options = {};
	var http = {};
	configs.forEach(function(config) {
		options = __assign(__assign(__assign({}, options), config.options), { headers: __assign(__assign({}, options.headers), config.headers) });
		if (config.credentials) options.credentials = config.credentials;
		http = __assign(__assign({}, http), config.http);
	});
	if (options.headers) options.headers = removeDuplicateHeaders(options.headers, http.preserveHeaderCase);
	var operationName = operation.operationName, extensions = operation.extensions, variables = operation.variables, query = operation.query;
	var body = {
		operationName,
		variables
	};
	if (http.includeExtensions) body.extensions = extensions;
	if (http.includeQuery) body.query = printer(query, print);
	return {
		options,
		body
	};
}
function removeDuplicateHeaders(headers, preserveHeaderCase) {
	if (!preserveHeaderCase) {
		var normalizedHeaders_1 = {};
		Object.keys(Object(headers)).forEach(function(name) {
			normalizedHeaders_1[name.toLowerCase()] = headers[name];
		});
		return normalizedHeaders_1;
	}
	var headerData = {};
	Object.keys(Object(headers)).forEach(function(name) {
		headerData[name.toLowerCase()] = {
			originalName: name,
			value: headers[name]
		};
	});
	var normalizedHeaders = {};
	Object.keys(headerData).forEach(function(name) {
		normalizedHeaders[headerData[name].originalName] = headerData[name].value;
	});
	return normalizedHeaders;
}
//#endregion
//#region node_modules/@apollo/client/link/http/checkFetcher.js
var checkFetcher = function(fetcher) {
	if (!fetcher && typeof fetch === "undefined") throw newInvariantError(51);
};
//#endregion
//#region node_modules/@apollo/client/link/http/createSignalIfSupported.js
/**
* @deprecated
* This is not used internally any more and will be removed in
* the next major version of Apollo Client.
*/
var createSignalIfSupported = function() {
	if (typeof AbortController === "undefined") return {
		controller: false,
		signal: false
	};
	var controller = new AbortController();
	return {
		controller,
		signal: controller.signal
	};
};
//#endregion
//#region node_modules/@apollo/client/link/http/selectURI.js
var selectURI = function(operation, fallbackURI) {
	var contextURI = operation.getContext().uri;
	if (contextURI) return contextURI;
	else if (typeof fallbackURI === "function") return fallbackURI(operation);
	else return fallbackURI || "/graphql";
};
//#endregion
//#region node_modules/@apollo/client/link/http/rewriteURIForGET.js
function rewriteURIForGET(chosenURI, body) {
	var queryParams = [];
	var addQueryParam = function(key, value) {
		queryParams.push("".concat(key, "=").concat(encodeURIComponent(value)));
	};
	if ("query" in body) addQueryParam("query", body.query);
	if (body.operationName) addQueryParam("operationName", body.operationName);
	if (body.variables) {
		var serializedVariables = void 0;
		try {
			serializedVariables = serializeFetchParameter(body.variables, "Variables map");
		} catch (parseError) {
			return { parseError };
		}
		addQueryParam("variables", serializedVariables);
	}
	if (body.extensions) {
		var serializedExtensions = void 0;
		try {
			serializedExtensions = serializeFetchParameter(body.extensions, "Extensions map");
		} catch (parseError) {
			return { parseError };
		}
		addQueryParam("extensions", serializedExtensions);
	}
	var fragment = "", preFragment = chosenURI;
	var fragmentStart = chosenURI.indexOf("#");
	if (fragmentStart !== -1) {
		fragment = chosenURI.substr(fragmentStart);
		preFragment = chosenURI.substr(0, fragmentStart);
	}
	var queryParamsPrefix = preFragment.indexOf("?") === -1 ? "?" : "&";
	return { newURI: preFragment + queryParamsPrefix + queryParams.join("&") + fragment };
}
//#endregion
//#region node_modules/@apollo/client/link/http/createHttpLink.js
var backupFetch = maybe$1(function() {
	return fetch;
});
var createHttpLink$1 = function(linkOptions) {
	if (linkOptions === void 0) linkOptions = {};
	var _a = linkOptions.uri, uri = _a === void 0 ? "/graphql" : _a, preferredFetch = linkOptions.fetch, _b = linkOptions.print, print = _b === void 0 ? defaultPrinter : _b, includeExtensions = linkOptions.includeExtensions, preserveHeaderCase = linkOptions.preserveHeaderCase, useGETForQueries = linkOptions.useGETForQueries, _c = linkOptions.includeUnusedVariables, includeUnusedVariables = _c === void 0 ? false : _c, requestOptions = __rest(linkOptions, [
		"uri",
		"fetch",
		"print",
		"includeExtensions",
		"preserveHeaderCase",
		"useGETForQueries",
		"includeUnusedVariables"
	]);
	if (globalThis.__DEV__ !== false) checkFetcher(preferredFetch || backupFetch);
	var linkConfig = {
		http: {
			includeExtensions,
			preserveHeaderCase
		},
		options: requestOptions.fetchOptions,
		credentials: requestOptions.credentials,
		headers: requestOptions.headers
	};
	return new ApolloLink(function(operation) {
		var chosenURI = selectURI(operation, uri);
		var context = operation.getContext();
		var clientAwarenessHeaders = {};
		if (context.clientAwareness) {
			var _a = context.clientAwareness, name_1 = _a.name, version = _a.version;
			if (name_1) clientAwarenessHeaders["apollographql-client-name"] = name_1;
			if (version) clientAwarenessHeaders["apollographql-client-version"] = version;
		}
		var contextHeaders = __assign(__assign({}, clientAwarenessHeaders), context.headers);
		var contextConfig = {
			http: context.http,
			options: context.fetchOptions,
			credentials: context.credentials,
			headers: contextHeaders
		};
		if (hasDirectives(["client"], operation.query)) {
			if (globalThis.__DEV__ !== false) globalThis.__DEV__ !== false && invariant$1.warn(52);
			var transformedQuery = removeClientSetsFromDocument(operation.query);
			if (!transformedQuery) return fromError(/* @__PURE__ */ new Error("HttpLink: Trying to send a client-only query to the server. To send to the server, ensure a non-client field is added to the query or set the `transformOptions.removeClientFields` option to `true`."));
			operation.query = transformedQuery;
		}
		var _b = selectHttpOptionsAndBodyInternal(operation, print, fallbackHttpConfig, linkConfig, contextConfig), options = _b.options, body = _b.body;
		if (body.variables && !includeUnusedVariables) body.variables = filterOperationVariables(body.variables, operation.query);
		var controller;
		if (!options.signal && typeof AbortController !== "undefined") {
			controller = new AbortController();
			options.signal = controller.signal;
		}
		var definitionIsMutation = function(d) {
			return d.kind === "OperationDefinition" && d.operation === "mutation";
		};
		var definitionIsSubscription = function(d) {
			return d.kind === "OperationDefinition" && d.operation === "subscription";
		};
		var isSubscription = definitionIsSubscription(getMainDefinition(operation.query));
		var hasDefer = hasDirectives(["defer"], operation.query);
		if (useGETForQueries && !operation.query.definitions.some(definitionIsMutation)) options.method = "GET";
		if (hasDefer || isSubscription) {
			options.headers = options.headers || {};
			var acceptHeader = "multipart/mixed;";
			if (isSubscription && hasDefer) globalThis.__DEV__ !== false && invariant$1.warn(53);
			if (isSubscription) acceptHeader += "boundary=graphql;subscriptionSpec=1.0,application/json";
			else if (hasDefer) acceptHeader += "deferSpec=20220824,application/json";
			options.headers.accept = acceptHeader;
		}
		if (options.method === "GET") {
			var _c = rewriteURIForGET(chosenURI, body), newURI = _c.newURI, parseError = _c.parseError;
			if (parseError) return fromError(parseError);
			chosenURI = newURI;
		} else try {
			options.body = serializeFetchParameter(body, "Payload");
		} catch (parseError) {
			return fromError(parseError);
		}
		return new Observable(function(observer) {
			var currentFetch = preferredFetch || maybe$1(function() {
				return fetch;
			}) || backupFetch;
			var observerNext = observer.next.bind(observer);
			currentFetch(chosenURI, options).then(function(response) {
				var _a;
				operation.setContext({ response });
				var ctype = (_a = response.headers) === null || _a === void 0 ? void 0 : _a.get("content-type");
				if (ctype !== null && /^multipart\/mixed/i.test(ctype)) return readMultipartBody(response, observerNext);
				else return parseAndCheckHttpResponse(operation)(response).then(observerNext);
			}).then(function() {
				controller = void 0;
				observer.complete();
			}).catch(function(err) {
				controller = void 0;
				handleError(err, observer);
			});
			return function() {
				if (controller) controller.abort();
			};
		});
	});
};
//#endregion
//#region node_modules/@apollo/client/link/http/HttpLink.js
var HttpLink = function(_super) {
	__extends(HttpLink, _super);
	function HttpLink(options) {
		if (options === void 0) options = {};
		var _this = _super.call(this, createHttpLink$1(options).request) || this;
		_this.options = options;
		return _this;
	}
	return HttpLink;
}(ApolloLink);
//#endregion
//#region node_modules/@wry/equality/lib/index.js
var { toString, hasOwnProperty: hasOwnProperty$2 } = Object.prototype;
var fnToStr = Function.prototype.toString;
var previousComparisons = /* @__PURE__ */ new Map();
/**
* Performs a deep equality check on two JavaScript values, tolerating cycles.
*/
function equal(a, b) {
	try {
		return check(a, b);
	} finally {
		previousComparisons.clear();
	}
}
function check(a, b) {
	if (a === b) return true;
	const aTag = toString.call(a);
	if (aTag !== toString.call(b)) return false;
	switch (aTag) {
		case "[object Array]": if (a.length !== b.length) return false;
		case "[object Object]": {
			if (previouslyCompared(a, b)) return true;
			const aKeys = definedKeys(a);
			const bKeys = definedKeys(b);
			const keyCount = aKeys.length;
			if (keyCount !== bKeys.length) return false;
			for (let k = 0; k < keyCount; ++k) if (!hasOwnProperty$2.call(b, aKeys[k])) return false;
			for (let k = 0; k < keyCount; ++k) {
				const key = aKeys[k];
				if (!check(a[key], b[key])) return false;
			}
			return true;
		}
		case "[object Error]": return a.name === b.name && a.message === b.message;
		case "[object Number]": if (a !== a) return b !== b;
		case "[object Boolean]":
		case "[object Date]": return +a === +b;
		case "[object RegExp]":
		case "[object String]": return a == `${b}`;
		case "[object Map]":
		case "[object Set]": {
			if (a.size !== b.size) return false;
			if (previouslyCompared(a, b)) return true;
			const aIterator = a.entries();
			const isMap = aTag === "[object Map]";
			while (true) {
				const info = aIterator.next();
				if (info.done) break;
				const [aKey, aValue] = info.value;
				if (!b.has(aKey)) return false;
				if (isMap && !check(aValue, b.get(aKey))) return false;
			}
			return true;
		}
		case "[object Uint16Array]":
		case "[object Uint8Array]":
		case "[object Uint32Array]":
		case "[object Int32Array]":
		case "[object Int8Array]":
		case "[object Int16Array]":
		case "[object ArrayBuffer]":
			a = new Uint8Array(a);
			b = new Uint8Array(b);
		case "[object DataView]": {
			let len = a.byteLength;
			if (len === b.byteLength) while (len-- && a[len] === b[len]);
			return len === -1;
		}
		case "[object AsyncFunction]":
		case "[object GeneratorFunction]":
		case "[object AsyncGeneratorFunction]":
		case "[object Function]": {
			const aCode = fnToStr.call(a);
			if (aCode !== fnToStr.call(b)) return false;
			return !endsWith(aCode, nativeCodeSuffix);
		}
	}
	return false;
}
function definedKeys(obj) {
	return Object.keys(obj).filter(isDefinedKey, obj);
}
function isDefinedKey(key) {
	return this[key] !== void 0;
}
var nativeCodeSuffix = "{ [native code] }";
function endsWith(full, suffix) {
	const fromIndex = full.length - suffix.length;
	return fromIndex >= 0 && full.indexOf(suffix, fromIndex) === fromIndex;
}
function previouslyCompared(a, b) {
	let bSet = previousComparisons.get(a);
	if (bSet) {
		if (bSet.has(b)) return true;
	} else previousComparisons.set(a, bSet = /* @__PURE__ */ new Set());
	bSet.add(b);
	return false;
}
//#endregion
//#region node_modules/@apollo/client/core/equalByQuery.js
function equalByQuery(query, _a, _b, variables) {
	var aData = _a.data, aRest = __rest(_a, ["data"]);
	var bData = _b.data;
	return equal(aRest, __rest(_b, ["data"])) && equalBySelectionSet(getMainDefinition(query).selectionSet, aData, bData, {
		fragmentMap: createFragmentMap(getFragmentDefinitions(query)),
		variables
	});
}
function equalBySelectionSet(selectionSet, aResult, bResult, context) {
	if (aResult === bResult) return true;
	var seenSelections = /* @__PURE__ */ new Set();
	return selectionSet.selections.every(function(selection) {
		if (seenSelections.has(selection)) return true;
		seenSelections.add(selection);
		if (!shouldInclude(selection, context.variables)) return true;
		if (selectionHasNonreactiveDirective(selection)) return true;
		if (isField(selection)) {
			var resultKey = resultKeyNameFromField(selection);
			var aResultChild = aResult && aResult[resultKey];
			var bResultChild = bResult && bResult[resultKey];
			var childSelectionSet = selection.selectionSet;
			if (!childSelectionSet) return equal(aResultChild, bResultChild);
			var aChildIsArray = Array.isArray(aResultChild);
			var bChildIsArray = Array.isArray(bResultChild);
			if (aChildIsArray !== bChildIsArray) return false;
			if (aChildIsArray && bChildIsArray) {
				var length_1 = aResultChild.length;
				if (bResultChild.length !== length_1) return false;
				for (var i = 0; i < length_1; ++i) if (!equalBySelectionSet(childSelectionSet, aResultChild[i], bResultChild[i], context)) return false;
				return true;
			}
			return equalBySelectionSet(childSelectionSet, aResultChild, bResultChild, context);
		} else {
			var fragment = getFragmentFromSelection(selection, context.fragmentMap);
			if (fragment) {
				if (selectionHasNonreactiveDirective(fragment)) return true;
				return equalBySelectionSet(fragment.selectionSet, aResult, bResult, context);
			}
		}
	});
}
function selectionHasNonreactiveDirective(selection) {
	return !!selection.directives && selection.directives.some(directiveIsNonreactive);
}
function directiveIsNonreactive(dir) {
	return dir.name.value === "nonreactive";
}
//#endregion
//#region node_modules/@apollo/client/masking/utils.js
var MapImpl = canUseWeakMap ? WeakMap : Map;
var SetImpl = canUseWeakSet ? WeakSet : Set;
/** @internal */
var disableWarningsSlot = new Slot();
var issuedWarning = false;
function warnOnImproperCacheImplementation() {
	if (!issuedWarning) {
		issuedWarning = true;
		globalThis.__DEV__ !== false && invariant$1.warn(64);
	}
}
//#endregion
//#region node_modules/@apollo/client/masking/maskDefinition.js
function maskDefinition(data, selectionSet, context) {
	return disableWarningsSlot.withValue(true, function() {
		var masked = maskSelectionSet(data, selectionSet, context, false);
		if (Object.isFrozen(data)) maybeDeepFreeze(masked);
		return masked;
	});
}
function getMutableTarget(data, mutableTargets) {
	if (mutableTargets.has(data)) return mutableTargets.get(data);
	var mutableTarget = Array.isArray(data) ? [] : Object.create(null);
	mutableTargets.set(data, mutableTarget);
	return mutableTarget;
}
function maskSelectionSet(data, selectionSet, context, migration, path) {
	var _a;
	var knownChanged = context.knownChanged;
	var memo = getMutableTarget(data, context.mutableTargets);
	if (Array.isArray(data)) {
		for (var _i = 0, _b = Array.from(data.entries()); _i < _b.length; _i++) {
			var _c = _b[_i], index = _c[0], item = _c[1];
			if (item === null) {
				memo[index] = null;
				continue;
			}
			var masked = maskSelectionSet(item, selectionSet, context, migration, globalThis.__DEV__ !== false ? "".concat(path || "", "[").concat(index, "]") : void 0);
			if (knownChanged.has(masked)) knownChanged.add(memo);
			memo[index] = masked;
		}
		return knownChanged.has(memo) ? memo : data;
	}
	for (var _d = 0, _e = selectionSet.selections; _d < _e.length; _d++) {
		var selection = _e[_d];
		var value = void 0;
		if (migration) knownChanged.add(memo);
		if (selection.kind === Kind.FIELD) {
			var keyName = resultKeyNameFromField(selection);
			var childSelectionSet = selection.selectionSet;
			value = memo[keyName] || data[keyName];
			if (value === void 0) continue;
			if (childSelectionSet && value !== null) {
				var masked = maskSelectionSet(data[keyName], childSelectionSet, context, migration, globalThis.__DEV__ !== false ? "".concat(path || "", ".").concat(keyName) : void 0);
				if (knownChanged.has(masked)) value = masked;
			}
			if (!(globalThis.__DEV__ !== false)) memo[keyName] = value;
			if (globalThis.__DEV__ !== false) if (migration && keyName !== "__typename" && !((_a = Object.getOwnPropertyDescriptor(memo, keyName)) === null || _a === void 0 ? void 0 : _a.value)) Object.defineProperty(memo, keyName, getAccessorWarningDescriptor(keyName, value, path || "", context.operationName, context.operationType));
			else {
				delete memo[keyName];
				memo[keyName] = value;
			}
		}
		if (selection.kind === Kind.INLINE_FRAGMENT && (!selection.typeCondition || context.cache.fragmentMatches(selection, data.__typename))) value = maskSelectionSet(data, selection.selectionSet, context, migration, path);
		if (selection.kind === Kind.FRAGMENT_SPREAD) {
			var fragmentName = selection.name.value;
			var fragment = context.fragmentMap[fragmentName] || (context.fragmentMap[fragmentName] = context.cache.lookupFragment(fragmentName));
			invariant$1(fragment, 59, fragmentName);
			var mode = getFragmentMaskMode(selection);
			if (mode !== "mask") value = maskSelectionSet(data, fragment.selectionSet, context, mode === "migrate", path);
		}
		if (knownChanged.has(value)) knownChanged.add(memo);
	}
	if ("__typename" in data && !("__typename" in memo)) memo.__typename = data.__typename;
	if (Object.keys(memo).length !== Object.keys(data).length) knownChanged.add(memo);
	return knownChanged.has(memo) ? memo : data;
}
function getAccessorWarningDescriptor(fieldName, value, path, operationName, operationType) {
	var getValue = function() {
		if (disableWarningsSlot.getValue()) return value;
		globalThis.__DEV__ !== false && invariant$1.warn(60, operationName ? "".concat(operationType, " '").concat(operationName, "'") : "anonymous ".concat(operationType), "".concat(path, ".").concat(fieldName).replace(/^\./, ""));
		getValue = function() {
			return value;
		};
		return value;
	};
	return {
		get: function() {
			return getValue();
		},
		set: function(newValue) {
			getValue = function() {
				return newValue;
			};
		},
		enumerable: true,
		configurable: true
	};
}
//#endregion
//#region node_modules/@apollo/client/masking/maskFragment.js
/** @internal */
function maskFragment(data, document, cache, fragmentName) {
	if (!cache.fragmentMatches) {
		if (globalThis.__DEV__ !== false) warnOnImproperCacheImplementation();
		return data;
	}
	var fragments = document.definitions.filter(function(node) {
		return node.kind === Kind.FRAGMENT_DEFINITION;
	});
	if (typeof fragmentName === "undefined") {
		invariant$1(fragments.length === 1, 61, fragments.length);
		fragmentName = fragments[0].name.value;
	}
	var fragment = fragments.find(function(fragment) {
		return fragment.name.value === fragmentName;
	});
	invariant$1(!!fragment, 62, fragmentName);
	if (data == null) return data;
	if (equal(data, {})) return data;
	return maskDefinition(data, fragment.selectionSet, {
		operationType: "fragment",
		operationName: fragment.name.value,
		fragmentMap: createFragmentMap(getFragmentDefinitions(document)),
		cache,
		mutableTargets: new MapImpl(),
		knownChanged: new SetImpl()
	});
}
//#endregion
//#region node_modules/@apollo/client/masking/maskOperation.js
/** @internal */
function maskOperation(data, document, cache) {
	var _a;
	if (!cache.fragmentMatches) {
		if (globalThis.__DEV__ !== false) warnOnImproperCacheImplementation();
		return data;
	}
	var definition = getOperationDefinition(document);
	invariant$1(definition, 63);
	if (data == null) return data;
	return maskDefinition(data, definition.selectionSet, {
		operationType: definition.operation,
		operationName: (_a = definition.name) === null || _a === void 0 ? void 0 : _a.value,
		fragmentMap: createFragmentMap(getFragmentDefinitions(document)),
		cache,
		mutableTargets: new MapImpl(),
		knownChanged: new SetImpl()
	});
}
//#endregion
//#region node_modules/@apollo/client/cache/core/cache.js
var ApolloCache = function() {
	function ApolloCache() {
		this.assumeImmutableResults = false;
		this.getFragmentDoc = wrap(getFragmentQueryDocument, {
			max: cacheSizes["cache.fragmentQueryDocuments"] || 1e3,
			cache: WeakCache
		});
	}
	ApolloCache.prototype.lookupFragment = function(fragmentName) {
		return null;
	};
	ApolloCache.prototype.batch = function(options) {
		var _this = this;
		var optimisticId = typeof options.optimistic === "string" ? options.optimistic : options.optimistic === false ? null : void 0;
		var updateResult;
		this.performTransaction(function() {
			return updateResult = options.update(_this);
		}, optimisticId);
		return updateResult;
	};
	ApolloCache.prototype.recordOptimisticTransaction = function(transaction, optimisticId) {
		this.performTransaction(transaction, optimisticId);
	};
	ApolloCache.prototype.transformDocument = function(document) {
		return document;
	};
	ApolloCache.prototype.transformForLink = function(document) {
		return document;
	};
	ApolloCache.prototype.identify = function(object) {};
	ApolloCache.prototype.gc = function() {
		return [];
	};
	ApolloCache.prototype.modify = function(options) {
		return false;
	};
	ApolloCache.prototype.readQuery = function(options, optimistic) {
		var _this = this;
		if (optimistic === void 0) optimistic = !!options.optimistic;
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.readQuery");
		return muteDeprecations("canonizeResults", function() {
			return _this.read(__assign(__assign({}, options), {
				rootId: options.id || "ROOT_QUERY",
				optimistic
			}));
		});
	};
	/** {@inheritDoc @apollo/client!ApolloClient#watchFragment:member(1)} */
	ApolloCache.prototype.watchFragment = function(options) {
		var _this = this;
		var fragment = options.fragment, fragmentName = options.fragmentName, from = options.from, _a = options.optimistic, optimistic = _a === void 0 ? true : _a, otherOptions = __rest(options, [
			"fragment",
			"fragmentName",
			"from",
			"optimistic"
		]);
		var query = this.getFragmentDoc(fragment, fragmentName);
		var id = typeof from === "undefined" || typeof from === "string" ? from : this.identify(from);
		var dataMasking = !!options[Symbol.for("apollo.dataMasking")];
		if (globalThis.__DEV__ !== false) {
			var actualFragmentName = fragmentName || getFragmentDefinition(fragment).name.value;
			if (!id) globalThis.__DEV__ !== false && invariant$1.warn(1, actualFragmentName);
		}
		var diffOptions = __assign(__assign({}, otherOptions), {
			returnPartialData: true,
			id,
			query,
			optimistic
		});
		var latestDiff;
		return new Observable(function(observer) {
			return _this.watch(__assign(__assign({}, diffOptions), {
				immediate: true,
				callback: function(diff) {
					var data = dataMasking ? maskFragment(diff.result, fragment, _this, fragmentName) : diff.result;
					if (latestDiff && equalByQuery(query, { data: latestDiff.result }, { data }, options.variables)) return;
					var result = {
						data,
						complete: !!diff.complete
					};
					if (diff.missing) result.missing = mergeDeepArray(diff.missing.map(function(error) {
						return error.missing;
					}));
					latestDiff = __assign(__assign({}, diff), { result: data });
					observer.next(result);
				}
			}));
		});
	};
	ApolloCache.prototype.readFragment = function(options, optimistic) {
		var _this = this;
		if (optimistic === void 0) optimistic = !!options.optimistic;
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.readFragment");
		return muteDeprecations("canonizeResults", function() {
			return _this.read(__assign(__assign({}, options), {
				query: _this.getFragmentDoc(options.fragment, options.fragmentName),
				rootId: options.id,
				optimistic
			}));
		});
	};
	ApolloCache.prototype.writeQuery = function(_a) {
		var id = _a.id, data = _a.data, options = __rest(_a, ["id", "data"]);
		return this.write(Object.assign(options, {
			dataId: id || "ROOT_QUERY",
			result: data
		}));
	};
	ApolloCache.prototype.writeFragment = function(_a) {
		var id = _a.id, data = _a.data, fragment = _a.fragment, fragmentName = _a.fragmentName, options = __rest(_a, [
			"id",
			"data",
			"fragment",
			"fragmentName"
		]);
		return this.write(Object.assign(options, {
			query: this.getFragmentDoc(fragment, fragmentName),
			dataId: id,
			result: data
		}));
	};
	ApolloCache.prototype.updateQuery = function(options, update) {
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.updateQuery");
		return this.batch({ update: function(cache) {
			var value = muteDeprecations("canonizeResults", function() {
				return cache.readQuery(options);
			});
			var data = update(value);
			if (data === void 0 || data === null) return value;
			cache.writeQuery(__assign(__assign({}, options), { data }));
			return data;
		} });
	};
	ApolloCache.prototype.updateFragment = function(options, update) {
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.updateFragment");
		return this.batch({ update: function(cache) {
			var value = muteDeprecations("canonizeResults", function() {
				return cache.readFragment(options);
			});
			var data = update(value);
			if (data === void 0 || data === null) return value;
			cache.writeFragment(__assign(__assign({}, options), { data }));
			return data;
		} });
	};
	return ApolloCache;
}();
if (globalThis.__DEV__ !== false) ApolloCache.prototype.getMemoryInternals = getApolloCacheMemoryInternals;
//#endregion
//#region node_modules/@apollo/client/cache/core/types/Cache.js
var Cache;
Cache || (Cache = {});
//#endregion
//#region node_modules/@apollo/client/cache/core/types/common.js
var MissingFieldError = function(_super) {
	__extends(MissingFieldError, _super);
	function MissingFieldError(message, path, query, variables) {
		var _a;
		var _this = _super.call(this, message) || this;
		_this.message = message;
		_this.path = path;
		_this.query = query;
		_this.variables = variables;
		if (Array.isArray(_this.path)) {
			_this.missing = _this.message;
			for (var i = _this.path.length - 1; i >= 0; --i) _this.missing = (_a = {}, _a[_this.path[i]] = _this.missing, _a);
		} else _this.missing = _this.path;
		_this.__proto__ = MissingFieldError.prototype;
		return _this;
	}
	return MissingFieldError;
}(Error);
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/helpers.js
var hasOwn = Object.prototype.hasOwnProperty;
function isNullish(value) {
	return value === null || value === void 0;
}
function defaultDataIdFromObject(_a, context) {
	var __typename = _a.__typename, id = _a.id, _id = _a._id;
	if (typeof __typename === "string") {
		if (context) context.keyObject = !isNullish(id) ? { id } : !isNullish(_id) ? { _id } : void 0;
		if (isNullish(id) && !isNullish(_id)) id = _id;
		if (!isNullish(id)) return "".concat(__typename, ":").concat(typeof id === "number" || typeof id === "string" ? id : JSON.stringify(id));
	}
}
var defaultConfig = {
	dataIdFromObject: defaultDataIdFromObject,
	addTypename: true,
	resultCaching: true,
	canonizeResults: false
};
function normalizeConfig(config) {
	return compact(defaultConfig, config);
}
function shouldCanonizeResults(config) {
	var value = config.canonizeResults;
	return value === void 0 ? defaultConfig.canonizeResults : value;
}
function getTypenameFromStoreObject(store, objectOrReference) {
	return isReference(objectOrReference) ? store.get(objectOrReference.__ref, "__typename") : objectOrReference && objectOrReference.__typename;
}
var TypeOrFieldNameRegExp = /^[_a-z][_0-9a-z]*/i;
function fieldNameFromStoreName(storeFieldName) {
	var match = storeFieldName.match(TypeOrFieldNameRegExp);
	return match ? match[0] : storeFieldName;
}
function selectionSetMatchesResult(selectionSet, result, variables) {
	if (isNonNullObject(result)) return isArray(result) ? result.every(function(item) {
		return selectionSetMatchesResult(selectionSet, item, variables);
	}) : selectionSet.selections.every(function(field) {
		if (isField(field) && shouldInclude(field, variables)) {
			var key = resultKeyNameFromField(field);
			return hasOwn.call(result, key) && (!field.selectionSet || selectionSetMatchesResult(field.selectionSet, result[key], variables));
		}
		return true;
	});
	return false;
}
function storeValueIsStoreObject(value) {
	return isNonNullObject(value) && !isReference(value) && !isArray(value);
}
function makeProcessedFieldsMerger() {
	return new DeepMerger();
}
function extractFragmentContext(document, fragments) {
	var fragmentMap = createFragmentMap(getFragmentDefinitions(document));
	return {
		fragmentMap,
		lookupFragment: function(name) {
			var def = fragmentMap[name];
			if (!def && fragments) def = fragments.lookup(name);
			return def || null;
		}
	};
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/entityStore.js
var DELETE = Object.create(null);
var delModifier = function() {
	return DELETE;
};
var INVALIDATE = Object.create(null);
var EntityStore = function() {
	function EntityStore(policies, group) {
		var _this = this;
		this.policies = policies;
		this.group = group;
		this.data = Object.create(null);
		this.rootIds = Object.create(null);
		this.refs = Object.create(null);
		this.getFieldValue = function(objectOrReference, storeFieldName) {
			return maybeDeepFreeze(isReference(objectOrReference) ? _this.get(objectOrReference.__ref, storeFieldName) : objectOrReference && objectOrReference[storeFieldName]);
		};
		this.canRead = function(objOrRef) {
			return isReference(objOrRef) ? _this.has(objOrRef.__ref) : typeof objOrRef === "object";
		};
		this.toReference = function(objOrIdOrRef, mergeIntoStore) {
			if (typeof objOrIdOrRef === "string") return makeReference(objOrIdOrRef);
			if (isReference(objOrIdOrRef)) return objOrIdOrRef;
			var id = _this.policies.identify(objOrIdOrRef)[0];
			if (id) {
				var ref = makeReference(id);
				if (mergeIntoStore) _this.merge(id, objOrIdOrRef);
				return ref;
			}
		};
	}
	EntityStore.prototype.toObject = function() {
		return __assign({}, this.data);
	};
	EntityStore.prototype.has = function(dataId) {
		return this.lookup(dataId, true) !== void 0;
	};
	EntityStore.prototype.get = function(dataId, fieldName) {
		this.group.depend(dataId, fieldName);
		if (hasOwn.call(this.data, dataId)) {
			var storeObject = this.data[dataId];
			if (storeObject && hasOwn.call(storeObject, fieldName)) return storeObject[fieldName];
		}
		if (fieldName === "__typename" && hasOwn.call(this.policies.rootTypenamesById, dataId)) return this.policies.rootTypenamesById[dataId];
		if (this instanceof Layer) return this.parent.get(dataId, fieldName);
	};
	EntityStore.prototype.lookup = function(dataId, dependOnExistence) {
		if (dependOnExistence) this.group.depend(dataId, "__exists");
		if (hasOwn.call(this.data, dataId)) return this.data[dataId];
		if (this instanceof Layer) return this.parent.lookup(dataId, dependOnExistence);
		if (this.policies.rootTypenamesById[dataId]) return Object.create(null);
	};
	EntityStore.prototype.merge = function(older, newer) {
		var _this = this;
		var dataId;
		if (isReference(older)) older = older.__ref;
		if (isReference(newer)) newer = newer.__ref;
		var existing = typeof older === "string" ? this.lookup(dataId = older) : older;
		var incoming = typeof newer === "string" ? this.lookup(dataId = newer) : newer;
		if (!incoming) return;
		invariant$1(typeof dataId === "string", 2);
		var merged = new DeepMerger(storeObjectReconciler).merge(existing, incoming);
		this.data[dataId] = merged;
		if (merged !== existing) {
			delete this.refs[dataId];
			if (this.group.caching) {
				var fieldsToDirty_1 = Object.create(null);
				if (!existing) fieldsToDirty_1.__exists = 1;
				Object.keys(incoming).forEach(function(storeFieldName) {
					if (!existing || existing[storeFieldName] !== merged[storeFieldName]) {
						fieldsToDirty_1[storeFieldName] = 1;
						var fieldName = fieldNameFromStoreName(storeFieldName);
						if (fieldName !== storeFieldName && !_this.policies.hasKeyArgs(merged.__typename, fieldName)) fieldsToDirty_1[fieldName] = 1;
						if (merged[storeFieldName] === void 0 && !(_this instanceof Layer)) delete merged[storeFieldName];
					}
				});
				if (fieldsToDirty_1.__typename && !(existing && existing.__typename) && this.policies.rootTypenamesById[dataId] === merged.__typename) delete fieldsToDirty_1.__typename;
				Object.keys(fieldsToDirty_1).forEach(function(fieldName) {
					return _this.group.dirty(dataId, fieldName);
				});
			}
		}
	};
	EntityStore.prototype.modify = function(dataId, fields) {
		var _this = this;
		var storeObject = this.lookup(dataId);
		if (storeObject) {
			var changedFields_1 = Object.create(null);
			var needToMerge_1 = false;
			var allDeleted_1 = true;
			var sharedDetails_1 = {
				DELETE,
				INVALIDATE,
				isReference,
				toReference: this.toReference,
				canRead: this.canRead,
				readField: function(fieldNameOrOptions, from) {
					return _this.policies.readField(typeof fieldNameOrOptions === "string" ? {
						fieldName: fieldNameOrOptions,
						from: from || makeReference(dataId)
					} : fieldNameOrOptions, { store: _this });
				}
			};
			Object.keys(storeObject).forEach(function(storeFieldName) {
				var fieldName = fieldNameFromStoreName(storeFieldName);
				var fieldValue = storeObject[storeFieldName];
				if (fieldValue === void 0) return;
				var modify = typeof fields === "function" ? fields : fields[storeFieldName] || fields[fieldName];
				if (modify) {
					var newValue = modify === delModifier ? DELETE : modify(maybeDeepFreeze(fieldValue), __assign(__assign({}, sharedDetails_1), {
						fieldName,
						storeFieldName,
						storage: _this.getStorage(dataId, storeFieldName)
					}));
					if (newValue === INVALIDATE) _this.group.dirty(dataId, storeFieldName);
					else {
						if (newValue === DELETE) newValue = void 0;
						if (newValue !== fieldValue) {
							changedFields_1[storeFieldName] = newValue;
							needToMerge_1 = true;
							fieldValue = newValue;
							if (globalThis.__DEV__ !== false) {
								var checkReference = function(ref) {
									if (_this.lookup(ref.__ref) === void 0) {
										globalThis.__DEV__ !== false && invariant$1.warn(3, ref);
										return true;
									}
								};
								if (isReference(newValue)) checkReference(newValue);
								else if (Array.isArray(newValue)) {
									var seenReference = false;
									var someNonReference = void 0;
									for (var _i = 0, newValue_1 = newValue; _i < newValue_1.length; _i++) {
										var value = newValue_1[_i];
										if (isReference(value)) {
											seenReference = true;
											if (checkReference(value)) break;
										} else if (typeof value === "object" && !!value) {
											if (_this.policies.identify(value)[0]) someNonReference = value;
										}
										if (seenReference && someNonReference !== void 0) {
											globalThis.__DEV__ !== false && invariant$1.warn(4, someNonReference);
											break;
										}
									}
								}
							}
						}
					}
				}
				if (fieldValue !== void 0) allDeleted_1 = false;
			});
			if (needToMerge_1) {
				this.merge(dataId, changedFields_1);
				if (allDeleted_1) {
					if (this instanceof Layer) this.data[dataId] = void 0;
					else delete this.data[dataId];
					this.group.dirty(dataId, "__exists");
				}
				return true;
			}
		}
		return false;
	};
	EntityStore.prototype.delete = function(dataId, fieldName, args) {
		var _a;
		var storeObject = this.lookup(dataId);
		if (storeObject) {
			var typename = this.getFieldValue(storeObject, "__typename");
			var storeFieldName = fieldName && args ? this.policies.getStoreFieldName({
				typename,
				fieldName,
				args
			}) : fieldName;
			return this.modify(dataId, storeFieldName ? (_a = {}, _a[storeFieldName] = delModifier, _a) : delModifier);
		}
		return false;
	};
	EntityStore.prototype.evict = function(options, limit) {
		var evicted = false;
		if (options.id) {
			if (hasOwn.call(this.data, options.id)) evicted = this.delete(options.id, options.fieldName, options.args);
			if (this instanceof Layer && this !== limit) evicted = this.parent.evict(options, limit) || evicted;
			if (options.fieldName || evicted) this.group.dirty(options.id, options.fieldName || "__exists");
		}
		return evicted;
	};
	EntityStore.prototype.clear = function() {
		this.replace(null);
	};
	EntityStore.prototype.extract = function() {
		var _this = this;
		var obj = this.toObject();
		var extraRootIds = [];
		this.getRootIdSet().forEach(function(id) {
			if (!hasOwn.call(_this.policies.rootTypenamesById, id)) extraRootIds.push(id);
		});
		if (extraRootIds.length) obj.__META = { extraRootIds: extraRootIds.sort() };
		return obj;
	};
	EntityStore.prototype.replace = function(newData) {
		var _this = this;
		Object.keys(this.data).forEach(function(dataId) {
			if (!(newData && hasOwn.call(newData, dataId))) _this.delete(dataId);
		});
		if (newData) {
			var __META = newData.__META, rest_1 = __rest(newData, ["__META"]);
			Object.keys(rest_1).forEach(function(dataId) {
				_this.merge(dataId, rest_1[dataId]);
			});
			if (__META) __META.extraRootIds.forEach(this.retain, this);
		}
	};
	EntityStore.prototype.retain = function(rootId) {
		return this.rootIds[rootId] = (this.rootIds[rootId] || 0) + 1;
	};
	EntityStore.prototype.release = function(rootId) {
		if (this.rootIds[rootId] > 0) {
			var count = --this.rootIds[rootId];
			if (!count) delete this.rootIds[rootId];
			return count;
		}
		return 0;
	};
	EntityStore.prototype.getRootIdSet = function(ids) {
		if (ids === void 0) ids = /* @__PURE__ */ new Set();
		Object.keys(this.rootIds).forEach(ids.add, ids);
		if (this instanceof Layer) this.parent.getRootIdSet(ids);
		else Object.keys(this.policies.rootTypenamesById).forEach(ids.add, ids);
		return ids;
	};
	EntityStore.prototype.gc = function() {
		var _this = this;
		var ids = this.getRootIdSet();
		var snapshot = this.toObject();
		ids.forEach(function(id) {
			if (hasOwn.call(snapshot, id)) {
				Object.keys(_this.findChildRefIds(id)).forEach(ids.add, ids);
				delete snapshot[id];
			}
		});
		var idsToRemove = Object.keys(snapshot);
		if (idsToRemove.length) {
			var root_1 = this;
			while (root_1 instanceof Layer) root_1 = root_1.parent;
			idsToRemove.forEach(function(id) {
				return root_1.delete(id);
			});
		}
		return idsToRemove;
	};
	EntityStore.prototype.findChildRefIds = function(dataId) {
		if (!hasOwn.call(this.refs, dataId)) {
			var found_1 = this.refs[dataId] = Object.create(null);
			var root = this.data[dataId];
			if (!root) return found_1;
			var workSet_1 = new Set([root]);
			workSet_1.forEach(function(obj) {
				if (isReference(obj)) found_1[obj.__ref] = true;
				if (isNonNullObject(obj)) Object.keys(obj).forEach(function(key) {
					var child = obj[key];
					if (isNonNullObject(child)) workSet_1.add(child);
				});
			});
		}
		return this.refs[dataId];
	};
	EntityStore.prototype.makeCacheKey = function() {
		return this.group.keyMaker.lookupArray(arguments);
	};
	return EntityStore;
}();
var CacheGroup = function() {
	function CacheGroup(caching, parent) {
		if (parent === void 0) parent = null;
		this.caching = caching;
		this.parent = parent;
		this.d = null;
		this.resetCaching();
	}
	CacheGroup.prototype.resetCaching = function() {
		this.d = this.caching ? dep() : null;
		this.keyMaker = new Trie(canUseWeakMap);
	};
	CacheGroup.prototype.depend = function(dataId, storeFieldName) {
		if (this.d) {
			this.d(makeDepKey(dataId, storeFieldName));
			var fieldName = fieldNameFromStoreName(storeFieldName);
			if (fieldName !== storeFieldName) this.d(makeDepKey(dataId, fieldName));
			if (this.parent) this.parent.depend(dataId, storeFieldName);
		}
	};
	CacheGroup.prototype.dirty = function(dataId, storeFieldName) {
		if (this.d) this.d.dirty(makeDepKey(dataId, storeFieldName), storeFieldName === "__exists" ? "forget" : "setDirty");
	};
	return CacheGroup;
}();
function makeDepKey(dataId, storeFieldName) {
	return storeFieldName + "#" + dataId;
}
function maybeDependOnExistenceOfEntity(store, entityId) {
	if (supportsResultCaching(store)) store.group.depend(entityId, "__exists");
}
(function(EntityStore) {
	EntityStore.Root = function(_super) {
		__extends(Root, _super);
		function Root(_a) {
			var policies = _a.policies, _b = _a.resultCaching, resultCaching = _b === void 0 ? true : _b, seed = _a.seed;
			var _this = _super.call(this, policies, new CacheGroup(resultCaching)) || this;
			_this.stump = new Stump(_this);
			_this.storageTrie = new Trie(canUseWeakMap);
			if (seed) _this.replace(seed);
			return _this;
		}
		Root.prototype.addLayer = function(layerId, replay) {
			return this.stump.addLayer(layerId, replay);
		};
		Root.prototype.removeLayer = function() {
			return this;
		};
		Root.prototype.getStorage = function() {
			return this.storageTrie.lookupArray(arguments);
		};
		return Root;
	}(EntityStore);
})(EntityStore || (EntityStore = {}));
var Layer = function(_super) {
	__extends(Layer, _super);
	function Layer(id, parent, replay, group) {
		var _this = _super.call(this, parent.policies, group) || this;
		_this.id = id;
		_this.parent = parent;
		_this.replay = replay;
		_this.group = group;
		replay(_this);
		return _this;
	}
	Layer.prototype.addLayer = function(layerId, replay) {
		return new Layer(layerId, this, replay, this.group);
	};
	Layer.prototype.removeLayer = function(layerId) {
		var _this = this;
		var parent = this.parent.removeLayer(layerId);
		if (layerId === this.id) {
			if (this.group.caching) Object.keys(this.data).forEach(function(dataId) {
				var ownStoreObject = _this.data[dataId];
				var parentStoreObject = parent["lookup"](dataId);
				if (!parentStoreObject) _this.delete(dataId);
				else if (!ownStoreObject) {
					_this.group.dirty(dataId, "__exists");
					Object.keys(parentStoreObject).forEach(function(storeFieldName) {
						_this.group.dirty(dataId, storeFieldName);
					});
				} else if (ownStoreObject !== parentStoreObject) Object.keys(ownStoreObject).forEach(function(storeFieldName) {
					if (!equal(ownStoreObject[storeFieldName], parentStoreObject[storeFieldName])) _this.group.dirty(dataId, storeFieldName);
				});
			});
			return parent;
		}
		if (parent === this.parent) return this;
		return parent.addLayer(this.id, this.replay);
	};
	Layer.prototype.toObject = function() {
		return __assign(__assign({}, this.parent.toObject()), this.data);
	};
	Layer.prototype.findChildRefIds = function(dataId) {
		var fromParent = this.parent.findChildRefIds(dataId);
		return hasOwn.call(this.data, dataId) ? __assign(__assign({}, fromParent), _super.prototype.findChildRefIds.call(this, dataId)) : fromParent;
	};
	Layer.prototype.getStorage = function() {
		var p = this.parent;
		while (p.parent) p = p.parent;
		return p.getStorage.apply(p, arguments);
	};
	return Layer;
}(EntityStore);
var Stump = function(_super) {
	__extends(Stump, _super);
	function Stump(root) {
		return _super.call(this, "EntityStore.Stump", root, function() {}, new CacheGroup(root.group.caching, root.group)) || this;
	}
	Stump.prototype.removeLayer = function() {
		return this;
	};
	Stump.prototype.merge = function(older, newer) {
		return this.parent.merge(older, newer);
	};
	return Stump;
}(Layer);
function storeObjectReconciler(existingObject, incomingObject, property) {
	var existingValue = existingObject[property];
	var incomingValue = incomingObject[property];
	return equal(existingValue, incomingValue) ? existingValue : incomingValue;
}
function supportsResultCaching(store) {
	return !!(store instanceof EntityStore && store.group.caching);
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/object-canon.js
function shallowCopy(value) {
	if (isNonNullObject(value)) return isArray(value) ? value.slice(0) : __assign({ __proto__: Object.getPrototypeOf(value) }, value);
	return value;
}
var ObjectCanon = function() {
	function ObjectCanon() {
		this.known = new (canUseWeakSet ? WeakSet : Set)();
		this.pool = new Trie(canUseWeakMap);
		this.passes = /* @__PURE__ */ new WeakMap();
		this.keysByJSON = /* @__PURE__ */ new Map();
		this.empty = this.admit({});
	}
	ObjectCanon.prototype.isKnown = function(value) {
		return isNonNullObject(value) && this.known.has(value);
	};
	ObjectCanon.prototype.pass = function(value) {
		if (isNonNullObject(value)) {
			var copy = shallowCopy(value);
			this.passes.set(copy, value);
			return copy;
		}
		return value;
	};
	ObjectCanon.prototype.admit = function(value) {
		var _this = this;
		if (isNonNullObject(value)) {
			var original = this.passes.get(value);
			if (original) return original;
			switch (Object.getPrototypeOf(value)) {
				case Array.prototype:
					if (this.known.has(value)) return value;
					var array = value.map(this.admit, this);
					var node = this.pool.lookupArray(array);
					if (!node.array) {
						this.known.add(node.array = array);
						if (globalThis.__DEV__ !== false) Object.freeze(array);
					}
					return node.array;
				case null:
				case Object.prototype:
					if (this.known.has(value)) return value;
					var proto_1 = Object.getPrototypeOf(value);
					var array_1 = [proto_1];
					var keys = this.sortedKeys(value);
					array_1.push(keys.json);
					var firstValueIndex_1 = array_1.length;
					keys.sorted.forEach(function(key) {
						array_1.push(_this.admit(value[key]));
					});
					var node = this.pool.lookupArray(array_1);
					if (!node.object) {
						var obj_1 = node.object = Object.create(proto_1);
						this.known.add(obj_1);
						keys.sorted.forEach(function(key, i) {
							obj_1[key] = array_1[firstValueIndex_1 + i];
						});
						if (globalThis.__DEV__ !== false) Object.freeze(obj_1);
					}
					return node.object;
			}
		}
		return value;
	};
	ObjectCanon.prototype.sortedKeys = function(obj) {
		var keys = Object.keys(obj);
		var node = this.pool.lookupArray(keys);
		if (!node.keys) {
			keys.sort();
			var json = JSON.stringify(keys);
			if (!(node.keys = this.keysByJSON.get(json))) this.keysByJSON.set(json, node.keys = {
				sorted: keys,
				json
			});
		}
		return node.keys;
	};
	return ObjectCanon;
}();
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/readFromStore.js
function execSelectionSetKeyArgs(options) {
	return [
		options.selectionSet,
		options.objectOrReference,
		options.context,
		options.context.canonizeResults
	];
}
var StoreReader = function() {
	function StoreReader(config) {
		var _this = this;
		this.knownResults = new (canUseWeakMap ? WeakMap : Map)();
		this.config = compact(config, {
			addTypename: config.addTypename !== false,
			canonizeResults: shouldCanonizeResults(config)
		});
		this.canon = config.canon || new ObjectCanon();
		this.executeSelectionSet = wrap(function(options) {
			var _a;
			var canonizeResults = options.context.canonizeResults;
			var peekArgs = execSelectionSetKeyArgs(options);
			peekArgs[3] = !canonizeResults;
			var other = (_a = _this.executeSelectionSet).peek.apply(_a, peekArgs);
			if (other) {
				if (canonizeResults) return __assign(__assign({}, other), { result: _this.canon.admit(other.result) });
				return other;
			}
			maybeDependOnExistenceOfEntity(options.context.store, options.enclosingRef.__ref);
			return _this.execSelectionSetImpl(options);
		}, {
			max: this.config.resultCacheMaxSize || cacheSizes["inMemoryCache.executeSelectionSet"] || 5e4,
			keyArgs: execSelectionSetKeyArgs,
			makeCacheKey: function(selectionSet, parent, context, canonizeResults) {
				if (supportsResultCaching(context.store)) return context.store.makeCacheKey(selectionSet, isReference(parent) ? parent.__ref : parent, context.varString, canonizeResults);
			}
		});
		this.executeSubSelectedArray = wrap(function(options) {
			maybeDependOnExistenceOfEntity(options.context.store, options.enclosingRef.__ref);
			return _this.execSubSelectedArrayImpl(options);
		}, {
			max: this.config.resultCacheMaxSize || cacheSizes["inMemoryCache.executeSubSelectedArray"] || 1e4,
			makeCacheKey: function(_a) {
				var field = _a.field, array = _a.array, context = _a.context;
				if (supportsResultCaching(context.store)) return context.store.makeCacheKey(field, array, context.varString);
			}
		});
	}
	StoreReader.prototype.resetCanon = function() {
		this.canon = new ObjectCanon();
	};
	/**
	* Given a store and a query, return as much of the result as possible and
	* identify if any data was missing from the store.
	*/
	StoreReader.prototype.diffQueryAgainstStore = function(_a) {
		var store = _a.store, query = _a.query, _b = _a.rootId, rootId = _b === void 0 ? "ROOT_QUERY" : _b, variables = _a.variables, _c = _a.returnPartialData, returnPartialData = _c === void 0 ? true : _c, _d = _a.canonizeResults, canonizeResults = _d === void 0 ? this.config.canonizeResults : _d;
		var policies = this.config.cache.policies;
		variables = __assign(__assign({}, getDefaultValues(getQueryDefinition(query))), variables);
		var rootRef = makeReference(rootId);
		var execResult = this.executeSelectionSet({
			selectionSet: getMainDefinition(query).selectionSet,
			objectOrReference: rootRef,
			enclosingRef: rootRef,
			context: __assign({
				store,
				query,
				policies,
				variables,
				varString: canonicalStringify(variables),
				canonizeResults
			}, extractFragmentContext(query, this.config.fragments))
		});
		var missing;
		if (execResult.missing) {
			missing = [new MissingFieldError(firstMissing(execResult.missing), execResult.missing, query, variables)];
			if (!returnPartialData) throw missing[0];
		}
		return {
			result: execResult.result,
			complete: !missing,
			missing
		};
	};
	StoreReader.prototype.isFresh = function(result, parent, selectionSet, context) {
		if (supportsResultCaching(context.store) && this.knownResults.get(result) === selectionSet) {
			var latest = this.executeSelectionSet.peek(selectionSet, parent, context, this.canon.isKnown(result));
			if (latest && result === latest.result) return true;
		}
		return false;
	};
	StoreReader.prototype.execSelectionSetImpl = function(_a) {
		var _this = this;
		var selectionSet = _a.selectionSet, objectOrReference = _a.objectOrReference, enclosingRef = _a.enclosingRef, context = _a.context;
		if (isReference(objectOrReference) && !context.policies.rootTypenamesById[objectOrReference.__ref] && !context.store.has(objectOrReference.__ref)) return {
			result: this.canon.empty,
			missing: "Dangling reference to missing ".concat(objectOrReference.__ref, " object")
		};
		var variables = context.variables, policies = context.policies;
		var typename = context.store.getFieldValue(objectOrReference, "__typename");
		var objectsToMerge = [];
		var missing;
		var missingMerger = new DeepMerger();
		if (this.config.addTypename && typeof typename === "string" && !policies.rootIdsByTypename[typename]) objectsToMerge.push({ __typename: typename });
		function handleMissing(result, resultName) {
			var _a;
			if (result.missing) missing = missingMerger.merge(missing, (_a = {}, _a[resultName] = result.missing, _a));
			return result.result;
		}
		var workSet = new Set(selectionSet.selections);
		workSet.forEach(function(selection) {
			var _a, _b;
			if (!shouldInclude(selection, variables)) return;
			if (isField(selection)) {
				var fieldValue = policies.readField({
					fieldName: selection.name.value,
					field: selection,
					variables: context.variables,
					from: objectOrReference
				}, context);
				var resultName = resultKeyNameFromField(selection);
				if (fieldValue === void 0) {
					if (!addTypenameToDocument.added(selection)) missing = missingMerger.merge(missing, (_a = {}, _a[resultName] = "Can't find field '".concat(selection.name.value, "' on ").concat(isReference(objectOrReference) ? objectOrReference.__ref + " object" : "object " + JSON.stringify(objectOrReference, null, 2)), _a));
				} else if (isArray(fieldValue)) {
					if (fieldValue.length > 0) fieldValue = handleMissing(_this.executeSubSelectedArray({
						field: selection,
						array: fieldValue,
						enclosingRef,
						context
					}), resultName);
				} else if (!selection.selectionSet) {
					if (context.canonizeResults) fieldValue = _this.canon.pass(fieldValue);
				} else if (fieldValue != null) fieldValue = handleMissing(_this.executeSelectionSet({
					selectionSet: selection.selectionSet,
					objectOrReference: fieldValue,
					enclosingRef: isReference(fieldValue) ? fieldValue : enclosingRef,
					context
				}), resultName);
				if (fieldValue !== void 0) objectsToMerge.push((_b = {}, _b[resultName] = fieldValue, _b));
			} else {
				var fragment = getFragmentFromSelection(selection, context.lookupFragment);
				if (!fragment && selection.kind === Kind.FRAGMENT_SPREAD) throw newInvariantError(10, selection.name.value);
				if (fragment && policies.fragmentMatches(fragment, typename)) fragment.selectionSet.selections.forEach(workSet.add, workSet);
			}
		});
		var finalResult = {
			result: mergeDeepArray(objectsToMerge),
			missing
		};
		var frozen = context.canonizeResults ? this.canon.admit(finalResult) : maybeDeepFreeze(finalResult);
		if (frozen.result) this.knownResults.set(frozen.result, selectionSet);
		return frozen;
	};
	StoreReader.prototype.execSubSelectedArrayImpl = function(_a) {
		var _this = this;
		var field = _a.field, array = _a.array, enclosingRef = _a.enclosingRef, context = _a.context;
		var missing;
		var missingMerger = new DeepMerger();
		function handleMissing(childResult, i) {
			var _a;
			if (childResult.missing) missing = missingMerger.merge(missing, (_a = {}, _a[i] = childResult.missing, _a));
			return childResult.result;
		}
		if (field.selectionSet) array = array.filter(context.store.canRead);
		array = array.map(function(item, i) {
			if (item === null) return null;
			if (isArray(item)) return handleMissing(_this.executeSubSelectedArray({
				field,
				array: item,
				enclosingRef,
				context
			}), i);
			if (field.selectionSet) return handleMissing(_this.executeSelectionSet({
				selectionSet: field.selectionSet,
				objectOrReference: item,
				enclosingRef: isReference(item) ? item : enclosingRef,
				context
			}), i);
			if (globalThis.__DEV__ !== false) assertSelectionSetForIdValue(context.store, field, item);
			return item;
		});
		return {
			result: context.canonizeResults ? this.canon.admit(array) : array,
			missing
		};
	};
	return StoreReader;
}();
function firstMissing(tree) {
	try {
		JSON.stringify(tree, function(_, value) {
			if (typeof value === "string") throw value;
			return value;
		});
	} catch (result) {
		return result;
	}
}
function assertSelectionSetForIdValue(store, field, fieldValue) {
	if (!field.selectionSet) {
		var workSet_1 = new Set([fieldValue]);
		workSet_1.forEach(function(value) {
			if (isNonNullObject(value)) {
				invariant$1(!isReference(value), 11, getTypenameFromStoreObject(store, value), field.name.value);
				Object.values(value).forEach(workSet_1.add, workSet_1);
			}
		});
	}
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/reactiveVars.js
var cacheSlot = new Slot();
var cacheInfoMap = /* @__PURE__ */ new WeakMap();
function getCacheInfo(cache) {
	var info = cacheInfoMap.get(cache);
	if (!info) cacheInfoMap.set(cache, info = {
		vars: /* @__PURE__ */ new Set(),
		dep: dep()
	});
	return info;
}
function forgetCache(cache) {
	getCacheInfo(cache).vars.forEach(function(rv) {
		return rv.forgetCache(cache);
	});
}
function recallCache(cache) {
	getCacheInfo(cache).vars.forEach(function(rv) {
		return rv.attachCache(cache);
	});
}
function makeVar(value) {
	var caches = /* @__PURE__ */ new Set();
	var listeners = /* @__PURE__ */ new Set();
	var rv = function(newValue) {
		if (arguments.length > 0) {
			if (value !== newValue) {
				value = newValue;
				caches.forEach(function(cache) {
					getCacheInfo(cache).dep.dirty(rv);
					broadcast(cache);
				});
				var oldListeners = Array.from(listeners);
				listeners.clear();
				oldListeners.forEach(function(listener) {
					return listener(value);
				});
			}
		} else {
			var cache = cacheSlot.getValue();
			if (cache) {
				attach(cache);
				getCacheInfo(cache).dep(rv);
			}
		}
		return value;
	};
	rv.onNextChange = function(listener) {
		listeners.add(listener);
		return function() {
			listeners.delete(listener);
		};
	};
	var attach = rv.attachCache = function(cache) {
		caches.add(cache);
		getCacheInfo(cache).vars.add(rv);
		return rv;
	};
	rv.forgetCache = function(cache) {
		return caches.delete(cache);
	};
	return rv;
}
function broadcast(cache) {
	if (cache.broadcastWatches) cache.broadcastWatches();
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/key-extractor.js
var specifierInfoCache = Object.create(null);
function lookupSpecifierInfo(spec) {
	var cacheKey = JSON.stringify(spec);
	return specifierInfoCache[cacheKey] || (specifierInfoCache[cacheKey] = Object.create(null));
}
function keyFieldsFnFromSpecifier(specifier) {
	var info = lookupSpecifierInfo(specifier);
	return info.keyFieldsFn || (info.keyFieldsFn = function(object, context) {
		var extract = function(from, key) {
			return context.readField(key, from);
		};
		var keyObject = context.keyObject = collectSpecifierPaths(specifier, function(schemaKeyPath) {
			var extracted = extractKeyPath(context.storeObject, schemaKeyPath, extract);
			if (extracted === void 0 && object !== context.storeObject && hasOwn.call(object, schemaKeyPath[0])) extracted = extractKeyPath(object, schemaKeyPath, extractKey);
			invariant$1(extracted !== void 0, 5, schemaKeyPath.join("."), object);
			return extracted;
		});
		return "".concat(context.typename, ":").concat(JSON.stringify(keyObject));
	});
}
function keyArgsFnFromSpecifier(specifier) {
	var info = lookupSpecifierInfo(specifier);
	return info.keyArgsFn || (info.keyArgsFn = function(args, _a) {
		var field = _a.field, variables = _a.variables, fieldName = _a.fieldName;
		var collected = collectSpecifierPaths(specifier, function(keyPath) {
			var firstKey = keyPath[0];
			var firstChar = firstKey.charAt(0);
			if (firstChar === "@") {
				if (field && isNonEmptyArray(field.directives)) {
					var directiveName_1 = firstKey.slice(1);
					var d = field.directives.find(function(d) {
						return d.name.value === directiveName_1;
					});
					var directiveArgs = d && argumentsObjectFromField(d, variables);
					return directiveArgs && extractKeyPath(directiveArgs, keyPath.slice(1));
				}
				return;
			}
			if (firstChar === "$") {
				var variableName = firstKey.slice(1);
				if (variables && hasOwn.call(variables, variableName)) {
					var varKeyPath = keyPath.slice(0);
					varKeyPath[0] = variableName;
					return extractKeyPath(variables, varKeyPath);
				}
				return;
			}
			if (args) return extractKeyPath(args, keyPath);
		});
		var suffix = JSON.stringify(collected);
		if (args || suffix !== "{}") fieldName += ":" + suffix;
		return fieldName;
	});
}
function collectSpecifierPaths(specifier, extractor) {
	var merger = new DeepMerger();
	return getSpecifierPaths(specifier).reduce(function(collected, path) {
		var _a;
		var toMerge = extractor(path);
		if (toMerge !== void 0) {
			for (var i = path.length - 1; i >= 0; --i) toMerge = (_a = {}, _a[path[i]] = toMerge, _a);
			collected = merger.merge(collected, toMerge);
		}
		return collected;
	}, Object.create(null));
}
function getSpecifierPaths(spec) {
	var info = lookupSpecifierInfo(spec);
	if (!info.paths) {
		var paths_1 = info.paths = [];
		var currentPath_1 = [];
		spec.forEach(function(s, i) {
			if (isArray(s)) {
				getSpecifierPaths(s).forEach(function(p) {
					return paths_1.push(currentPath_1.concat(p));
				});
				currentPath_1.length = 0;
			} else {
				currentPath_1.push(s);
				if (!isArray(spec[i + 1])) {
					paths_1.push(currentPath_1.slice(0));
					currentPath_1.length = 0;
				}
			}
		});
	}
	return info.paths;
}
function extractKey(object, key) {
	return object[key];
}
function extractKeyPath(object, path, extract) {
	extract = extract || extractKey;
	return normalize$1(path.reduce(function reducer(obj, key) {
		return isArray(obj) ? obj.map(function(child) {
			return reducer(child, key);
		}) : obj && extract(obj, key);
	}, object));
}
function normalize$1(value) {
	if (isNonNullObject(value)) {
		if (isArray(value)) return value.map(normalize$1);
		return collectSpecifierPaths(Object.keys(value).sort(), function(path) {
			return extractKeyPath(value, path);
		});
	}
	return value;
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/policies.js
function argsFromFieldSpecifier(spec) {
	return spec.args !== void 0 ? spec.args : spec.field ? argumentsObjectFromField(spec.field, spec.variables) : null;
}
var nullKeyFieldsFn = function() {};
var simpleKeyArgsFn = function(_args, context) {
	return context.fieldName;
};
var mergeTrueFn = function(existing, incoming, _a) {
	var mergeObjects = _a.mergeObjects;
	return mergeObjects(existing, incoming);
};
var mergeFalseFn = function(_, incoming) {
	return incoming;
};
var Policies = function() {
	function Policies(config) {
		this.config = config;
		this.typePolicies = Object.create(null);
		this.toBeAdded = Object.create(null);
		this.supertypeMap = /* @__PURE__ */ new Map();
		this.fuzzySubtypes = /* @__PURE__ */ new Map();
		this.rootIdsByTypename = Object.create(null);
		this.rootTypenamesById = Object.create(null);
		this.usingPossibleTypes = false;
		this.config = __assign({ dataIdFromObject: defaultDataIdFromObject }, config);
		this.cache = this.config.cache;
		this.setRootTypename("Query");
		this.setRootTypename("Mutation");
		this.setRootTypename("Subscription");
		if (config.possibleTypes) this.addPossibleTypes(config.possibleTypes);
		if (config.typePolicies) this.addTypePolicies(config.typePolicies);
	}
	Policies.prototype.identify = function(object, partialContext) {
		var _a;
		var policies = this;
		var typename = partialContext && (partialContext.typename || ((_a = partialContext.storeObject) === null || _a === void 0 ? void 0 : _a.__typename)) || object.__typename;
		if (typename === this.rootTypenamesById.ROOT_QUERY) return ["ROOT_QUERY"];
		var storeObject = partialContext && partialContext.storeObject || object;
		var context = __assign(__assign({}, partialContext), {
			typename,
			storeObject,
			readField: partialContext && partialContext.readField || function() {
				var options = normalizeReadFieldOptions(arguments, storeObject);
				return policies.readField(options, {
					store: policies.cache["data"],
					variables: options.variables
				});
			}
		});
		var id;
		var policy = typename && this.getTypePolicy(typename);
		var keyFn = policy && policy.keyFn || this.config.dataIdFromObject;
		disableWarningsSlot.withValue(true, function() {
			while (keyFn) {
				var specifierOrId = keyFn(__assign(__assign({}, object), storeObject), context);
				if (isArray(specifierOrId)) keyFn = keyFieldsFnFromSpecifier(specifierOrId);
				else {
					id = specifierOrId;
					break;
				}
			}
		});
		id = id ? String(id) : void 0;
		return context.keyObject ? [id, context.keyObject] : [id];
	};
	Policies.prototype.addTypePolicies = function(typePolicies) {
		var _this = this;
		Object.keys(typePolicies).forEach(function(typename) {
			var _a = typePolicies[typename], queryType = _a.queryType, mutationType = _a.mutationType, subscriptionType = _a.subscriptionType, incoming = __rest(_a, [
				"queryType",
				"mutationType",
				"subscriptionType"
			]);
			if (queryType) _this.setRootTypename("Query", typename);
			if (mutationType) _this.setRootTypename("Mutation", typename);
			if (subscriptionType) _this.setRootTypename("Subscription", typename);
			if (hasOwn.call(_this.toBeAdded, typename)) _this.toBeAdded[typename].push(incoming);
			else _this.toBeAdded[typename] = [incoming];
		});
	};
	Policies.prototype.updateTypePolicy = function(typename, incoming, existingFieldPolicies) {
		var existing = this.getTypePolicy(typename);
		var keyFields = incoming.keyFields, fields = incoming.fields;
		function setMerge(existing, merge) {
			existing.merge = typeof merge === "function" ? merge : merge === true ? mergeTrueFn : merge === false ? mergeFalseFn : existing.merge;
		}
		setMerge(existing, incoming.merge);
		existing.keyFn = keyFields === false ? nullKeyFieldsFn : isArray(keyFields) ? keyFieldsFnFromSpecifier(keyFields) : typeof keyFields === "function" ? keyFields : existing.keyFn;
		if (fields) Object.keys(fields).forEach(function(fieldName) {
			var existing = existingFieldPolicies[fieldName];
			if (!existing || (existing === null || existing === void 0 ? void 0 : existing.typename) !== typename) existing = existingFieldPolicies[fieldName] = { typename };
			var incoming = fields[fieldName];
			if (typeof incoming === "function") existing.read = incoming;
			else {
				var keyArgs = incoming.keyArgs, read = incoming.read, merge = incoming.merge;
				existing.keyFn = keyArgs === false ? simpleKeyArgsFn : isArray(keyArgs) ? keyArgsFnFromSpecifier(keyArgs) : typeof keyArgs === "function" ? keyArgs : existing.keyFn;
				if (typeof read === "function") existing.read = read;
				setMerge(existing, merge);
			}
			if (existing.read && existing.merge) existing.keyFn = existing.keyFn || simpleKeyArgsFn;
		});
	};
	Policies.prototype.setRootTypename = function(which, typename) {
		if (typename === void 0) typename = which;
		var rootId = "ROOT_" + which.toUpperCase();
		var old = this.rootTypenamesById[rootId];
		if (typename !== old) {
			invariant$1(!old || old === which, 6, which);
			if (old) delete this.rootIdsByTypename[old];
			this.rootIdsByTypename[typename] = rootId;
			this.rootTypenamesById[rootId] = typename;
		}
	};
	Policies.prototype.addPossibleTypes = function(possibleTypes) {
		var _this = this;
		this.usingPossibleTypes = true;
		Object.keys(possibleTypes).forEach(function(supertype) {
			_this.getSupertypeSet(supertype, true);
			possibleTypes[supertype].forEach(function(subtype) {
				_this.getSupertypeSet(subtype, true).add(supertype);
				var match = subtype.match(TypeOrFieldNameRegExp);
				if (!match || match[0] !== subtype) _this.fuzzySubtypes.set(subtype, new RegExp(subtype));
			});
		});
	};
	Policies.prototype.getTypePolicy = function(typename) {
		var _this = this;
		if (!hasOwn.call(this.typePolicies, typename)) {
			var policy_1 = this.typePolicies[typename] = Object.create(null);
			policy_1.fields = Object.create(null);
			var supertypes_1 = this.supertypeMap.get(typename);
			if (!supertypes_1 && this.fuzzySubtypes.size) {
				supertypes_1 = this.getSupertypeSet(typename, true);
				this.fuzzySubtypes.forEach(function(regExp, fuzzy) {
					if (regExp.test(typename)) {
						var fuzzySupertypes = _this.supertypeMap.get(fuzzy);
						if (fuzzySupertypes) fuzzySupertypes.forEach(function(supertype) {
							return supertypes_1.add(supertype);
						});
					}
				});
			}
			if (supertypes_1 && supertypes_1.size) supertypes_1.forEach(function(supertype) {
				var _a = _this.getTypePolicy(supertype), fields = _a.fields, rest = __rest(_a, ["fields"]);
				Object.assign(policy_1, rest);
				Object.assign(policy_1.fields, fields);
			});
		}
		var inbox = this.toBeAdded[typename];
		if (inbox && inbox.length) inbox.splice(0).forEach(function(policy) {
			_this.updateTypePolicy(typename, policy, _this.typePolicies[typename].fields);
		});
		return this.typePolicies[typename];
	};
	Policies.prototype.getFieldPolicy = function(typename, fieldName) {
		if (typename) return this.getTypePolicy(typename).fields[fieldName];
	};
	Policies.prototype.getSupertypeSet = function(subtype, createIfMissing) {
		var supertypeSet = this.supertypeMap.get(subtype);
		if (!supertypeSet && createIfMissing) this.supertypeMap.set(subtype, supertypeSet = /* @__PURE__ */ new Set());
		return supertypeSet;
	};
	Policies.prototype.fragmentMatches = function(fragment, typename, result, variables) {
		var _this = this;
		if (!fragment.typeCondition) return true;
		if (!typename) return false;
		var supertype = fragment.typeCondition.name.value;
		if (typename === supertype) return true;
		if (this.usingPossibleTypes && this.supertypeMap.has(supertype)) {
			var typenameSupertypeSet = this.getSupertypeSet(typename, true);
			var workQueue_1 = [typenameSupertypeSet];
			var maybeEnqueue_1 = function(subtype) {
				var supertypeSet = _this.getSupertypeSet(subtype, false);
				if (supertypeSet && supertypeSet.size && workQueue_1.indexOf(supertypeSet) < 0) workQueue_1.push(supertypeSet);
			};
			var needToCheckFuzzySubtypes = !!(result && this.fuzzySubtypes.size);
			var checkingFuzzySubtypes = false;
			for (var i = 0; i < workQueue_1.length; ++i) {
				var supertypeSet = workQueue_1[i];
				if (supertypeSet.has(supertype)) {
					if (!typenameSupertypeSet.has(supertype)) {
						if (checkingFuzzySubtypes) globalThis.__DEV__ !== false && invariant$1.warn(7, typename, supertype);
						typenameSupertypeSet.add(supertype);
					}
					return true;
				}
				supertypeSet.forEach(maybeEnqueue_1);
				if (needToCheckFuzzySubtypes && i === workQueue_1.length - 1 && selectionSetMatchesResult(fragment.selectionSet, result, variables)) {
					needToCheckFuzzySubtypes = false;
					checkingFuzzySubtypes = true;
					this.fuzzySubtypes.forEach(function(regExp, fuzzyString) {
						var match = typename.match(regExp);
						if (match && match[0] === typename) maybeEnqueue_1(fuzzyString);
					});
				}
			}
		}
		return false;
	};
	Policies.prototype.hasKeyArgs = function(typename, fieldName) {
		var policy = this.getFieldPolicy(typename, fieldName);
		return !!(policy && policy.keyFn);
	};
	Policies.prototype.getStoreFieldName = function(fieldSpec) {
		var typename = fieldSpec.typename, fieldName = fieldSpec.fieldName;
		var policy = this.getFieldPolicy(typename, fieldName);
		var storeFieldName;
		var keyFn = policy && policy.keyFn;
		if (keyFn && typename) {
			var context = {
				typename,
				fieldName,
				field: fieldSpec.field || null,
				variables: fieldSpec.variables
			};
			var args = argsFromFieldSpecifier(fieldSpec);
			while (keyFn) {
				var specifierOrString = keyFn(args, context);
				if (isArray(specifierOrString)) keyFn = keyArgsFnFromSpecifier(specifierOrString);
				else {
					storeFieldName = specifierOrString || fieldName;
					break;
				}
			}
		}
		if (storeFieldName === void 0) storeFieldName = fieldSpec.field ? storeKeyNameFromField(fieldSpec.field, fieldSpec.variables) : getStoreKeyName(fieldName, argsFromFieldSpecifier(fieldSpec));
		if (storeFieldName === false) return fieldName;
		return fieldName === fieldNameFromStoreName(storeFieldName) ? storeFieldName : fieldName + ":" + storeFieldName;
	};
	Policies.prototype.readField = function(options, context) {
		var objectOrReference = options.from;
		if (!objectOrReference) return;
		if (!(options.field || options.fieldName)) return;
		if (options.typename === void 0) {
			var typename = context.store.getFieldValue(objectOrReference, "__typename");
			if (typename) options.typename = typename;
		}
		var storeFieldName = this.getStoreFieldName(options);
		var fieldName = fieldNameFromStoreName(storeFieldName);
		var existing = context.store.getFieldValue(objectOrReference, storeFieldName);
		var policy = this.getFieldPolicy(options.typename, fieldName);
		var read = policy && policy.read;
		if (read) {
			var readOptions = makeFieldFunctionOptions(this, objectOrReference, options, context, context.store.getStorage(isReference(objectOrReference) ? objectOrReference.__ref : objectOrReference, storeFieldName));
			return cacheSlot.withValue(this.cache, read, [existing, readOptions]);
		}
		return existing;
	};
	Policies.prototype.getReadFunction = function(typename, fieldName) {
		var policy = this.getFieldPolicy(typename, fieldName);
		return policy && policy.read;
	};
	Policies.prototype.getMergeFunction = function(parentTypename, fieldName, childTypename) {
		var policy = this.getFieldPolicy(parentTypename, fieldName);
		var merge = policy && policy.merge;
		if (!merge && childTypename) {
			policy = this.getTypePolicy(childTypename);
			merge = policy && policy.merge;
		}
		return merge;
	};
	Policies.prototype.runMergeFunction = function(existing, incoming, _a, context, storage) {
		var field = _a.field, typename = _a.typename, merge = _a.merge;
		if (merge === mergeTrueFn) return makeMergeObjectsFunction(context.store)(existing, incoming);
		if (merge === mergeFalseFn) return incoming;
		if (context.overwrite) existing = void 0;
		return merge(existing, incoming, makeFieldFunctionOptions(this, void 0, {
			typename,
			fieldName: field.name.value,
			field,
			variables: context.variables
		}, context, storage || Object.create(null)));
	};
	return Policies;
}();
function makeFieldFunctionOptions(policies, objectOrReference, fieldSpec, context, storage) {
	var storeFieldName = policies.getStoreFieldName(fieldSpec);
	var fieldName = fieldNameFromStoreName(storeFieldName);
	var variables = fieldSpec.variables || context.variables;
	var _a = context.store, toReference = _a.toReference, canRead = _a.canRead;
	return {
		args: argsFromFieldSpecifier(fieldSpec),
		field: fieldSpec.field || null,
		fieldName,
		storeFieldName,
		variables,
		isReference,
		toReference,
		storage,
		cache: policies.cache,
		canRead,
		readField: function() {
			return policies.readField(normalizeReadFieldOptions(arguments, objectOrReference, variables), context);
		},
		mergeObjects: makeMergeObjectsFunction(context.store)
	};
}
function normalizeReadFieldOptions(readFieldArgs, objectOrReference, variables) {
	var fieldNameOrOptions = readFieldArgs[0], from = readFieldArgs[1], argc = readFieldArgs.length;
	var options;
	if (typeof fieldNameOrOptions === "string") options = {
		fieldName: fieldNameOrOptions,
		from: argc > 1 ? from : objectOrReference
	};
	else {
		options = __assign({}, fieldNameOrOptions);
		if (!hasOwn.call(options, "from")) options.from = objectOrReference;
	}
	if (globalThis.__DEV__ !== false && options.from === void 0) globalThis.__DEV__ !== false && invariant$1.warn(8, stringifyForDisplay(Array.from(readFieldArgs)));
	if (void 0 === options.variables) options.variables = variables;
	return options;
}
function makeMergeObjectsFunction(store) {
	return function mergeObjects(existing, incoming) {
		if (isArray(existing) || isArray(incoming)) throw newInvariantError(9);
		if (isNonNullObject(existing) && isNonNullObject(incoming)) {
			var eType = store.getFieldValue(existing, "__typename");
			var iType = store.getFieldValue(incoming, "__typename");
			if (eType && iType && eType !== iType) return incoming;
			if (isReference(existing) && storeValueIsStoreObject(incoming)) {
				store.merge(existing.__ref, incoming);
				return existing;
			}
			if (storeValueIsStoreObject(existing) && isReference(incoming)) {
				store.merge(existing, incoming.__ref);
				return incoming;
			}
			if (storeValueIsStoreObject(existing) && storeValueIsStoreObject(incoming)) return __assign(__assign({}, existing), incoming);
		}
		return incoming;
	};
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/writeToStore.js
function getContextFlavor(context, clientOnly, deferred) {
	var key = "".concat(clientOnly).concat(deferred);
	var flavored = context.flavors.get(key);
	if (!flavored) context.flavors.set(key, flavored = context.clientOnly === clientOnly && context.deferred === deferred ? context : __assign(__assign({}, context), {
		clientOnly,
		deferred
	}));
	return flavored;
}
var StoreWriter = function() {
	function StoreWriter(cache, reader, fragments) {
		this.cache = cache;
		this.reader = reader;
		this.fragments = fragments;
	}
	StoreWriter.prototype.writeToStore = function(store, _a) {
		var _this = this;
		var query = _a.query, result = _a.result, dataId = _a.dataId, variables = _a.variables, overwrite = _a.overwrite;
		var operationDefinition = getOperationDefinition(query);
		var merger = makeProcessedFieldsMerger();
		variables = __assign(__assign({}, getDefaultValues(operationDefinition)), variables);
		var context = __assign(__assign({
			store,
			written: Object.create(null),
			merge: function(existing, incoming) {
				return merger.merge(existing, incoming);
			},
			variables,
			varString: canonicalStringify(variables)
		}, extractFragmentContext(query, this.fragments)), {
			overwrite: !!overwrite,
			incomingById: /* @__PURE__ */ new Map(),
			clientOnly: false,
			deferred: false,
			flavors: /* @__PURE__ */ new Map()
		});
		var ref = this.processSelectionSet({
			result: result || Object.create(null),
			dataId,
			selectionSet: operationDefinition.selectionSet,
			mergeTree: { map: /* @__PURE__ */ new Map() },
			context
		});
		if (!isReference(ref)) throw newInvariantError(12, result);
		context.incomingById.forEach(function(_a, dataId) {
			var storeObject = _a.storeObject, mergeTree = _a.mergeTree, fieldNodeSet = _a.fieldNodeSet;
			var entityRef = makeReference(dataId);
			if (mergeTree && mergeTree.map.size) {
				var applied = _this.applyMerges(mergeTree, entityRef, storeObject, context);
				if (isReference(applied)) return;
				storeObject = applied;
			}
			if (globalThis.__DEV__ !== false && !context.overwrite) {
				var fieldsWithSelectionSets_1 = Object.create(null);
				fieldNodeSet.forEach(function(field) {
					if (field.selectionSet) fieldsWithSelectionSets_1[field.name.value] = true;
				});
				var hasSelectionSet_1 = function(storeFieldName) {
					return fieldsWithSelectionSets_1[fieldNameFromStoreName(storeFieldName)] === true;
				};
				var hasMergeFunction_1 = function(storeFieldName) {
					var childTree = mergeTree && mergeTree.map.get(storeFieldName);
					return Boolean(childTree && childTree.info && childTree.info.merge);
				};
				Object.keys(storeObject).forEach(function(storeFieldName) {
					if (hasSelectionSet_1(storeFieldName) && !hasMergeFunction_1(storeFieldName)) warnAboutDataLoss(entityRef, storeObject, storeFieldName, context.store);
				});
			}
			store.merge(dataId, storeObject);
		});
		store.retain(ref.__ref);
		return ref;
	};
	StoreWriter.prototype.processSelectionSet = function(_a) {
		var _this = this;
		var dataId = _a.dataId, result = _a.result, selectionSet = _a.selectionSet, context = _a.context, mergeTree = _a.mergeTree;
		var policies = this.cache.policies;
		var incoming = Object.create(null);
		var typename = dataId && policies.rootTypenamesById[dataId] || getTypenameFromResult(result, selectionSet, context.fragmentMap) || dataId && context.store.get(dataId, "__typename");
		if ("string" === typeof typename) incoming.__typename = typename;
		var readField = function() {
			var options = normalizeReadFieldOptions(arguments, incoming, context.variables);
			if (isReference(options.from)) {
				var info = context.incomingById.get(options.from.__ref);
				if (info) {
					var result_1 = policies.readField(__assign(__assign({}, options), { from: info.storeObject }), context);
					if (result_1 !== void 0) return result_1;
				}
			}
			return policies.readField(options, context);
		};
		var fieldNodeSet = /* @__PURE__ */ new Set();
		this.flattenFields(selectionSet, result, context, typename).forEach(function(context, field) {
			var _a;
			var value = result[resultKeyNameFromField(field)];
			fieldNodeSet.add(field);
			if (value !== void 0) {
				var storeFieldName = policies.getStoreFieldName({
					typename,
					fieldName: field.name.value,
					field,
					variables: context.variables
				});
				var childTree = getChildMergeTree(mergeTree, storeFieldName);
				var incomingValue = _this.processFieldValue(value, field, field.selectionSet ? getContextFlavor(context, false, false) : context, childTree);
				var childTypename = void 0;
				if (field.selectionSet && (isReference(incomingValue) || storeValueIsStoreObject(incomingValue))) childTypename = readField("__typename", incomingValue);
				var merge = policies.getMergeFunction(typename, field.name.value, childTypename);
				if (merge) childTree.info = {
					field,
					typename,
					merge
				};
				else maybeRecycleChildMergeTree(mergeTree, storeFieldName);
				incoming = context.merge(incoming, (_a = {}, _a[storeFieldName] = incomingValue, _a));
			} else if (globalThis.__DEV__ !== false && !context.clientOnly && !context.deferred && !addTypenameToDocument.added(field) && !policies.getReadFunction(typename, field.name.value)) globalThis.__DEV__ !== false && invariant$1.error(13, resultKeyNameFromField(field), result);
		});
		try {
			var _b = policies.identify(result, {
				typename,
				selectionSet,
				fragmentMap: context.fragmentMap,
				storeObject: incoming,
				readField
			}), id = _b[0], keyObject = _b[1];
			dataId = dataId || id;
			if (keyObject) incoming = context.merge(incoming, keyObject);
		} catch (e) {
			if (!dataId) throw e;
		}
		if ("string" === typeof dataId) {
			var dataRef = makeReference(dataId);
			var sets = context.written[dataId] || (context.written[dataId] = []);
			if (sets.indexOf(selectionSet) >= 0) return dataRef;
			sets.push(selectionSet);
			if (this.reader && this.reader.isFresh(result, dataRef, selectionSet, context)) return dataRef;
			var previous_1 = context.incomingById.get(dataId);
			if (previous_1) {
				previous_1.storeObject = context.merge(previous_1.storeObject, incoming);
				previous_1.mergeTree = mergeMergeTrees(previous_1.mergeTree, mergeTree);
				fieldNodeSet.forEach(function(field) {
					return previous_1.fieldNodeSet.add(field);
				});
			} else context.incomingById.set(dataId, {
				storeObject: incoming,
				mergeTree: mergeTreeIsEmpty(mergeTree) ? void 0 : mergeTree,
				fieldNodeSet
			});
			return dataRef;
		}
		return incoming;
	};
	StoreWriter.prototype.processFieldValue = function(value, field, context, mergeTree) {
		var _this = this;
		if (!field.selectionSet || value === null) return globalThis.__DEV__ !== false ? cloneDeep(value) : value;
		if (isArray(value)) return value.map(function(item, i) {
			var value = _this.processFieldValue(item, field, context, getChildMergeTree(mergeTree, i));
			maybeRecycleChildMergeTree(mergeTree, i);
			return value;
		});
		return this.processSelectionSet({
			result: value,
			selectionSet: field.selectionSet,
			context,
			mergeTree
		});
	};
	StoreWriter.prototype.flattenFields = function(selectionSet, result, context, typename) {
		if (typename === void 0) typename = getTypenameFromResult(result, selectionSet, context.fragmentMap);
		var fieldMap = /* @__PURE__ */ new Map();
		var policies = this.cache.policies;
		var limitingTrie = new Trie(false);
		(function flatten(selectionSet, inheritedContext) {
			var visitedNode = limitingTrie.lookup(selectionSet, inheritedContext.clientOnly, inheritedContext.deferred);
			if (visitedNode.visited) return;
			visitedNode.visited = true;
			selectionSet.selections.forEach(function(selection) {
				if (!shouldInclude(selection, context.variables)) return;
				var clientOnly = inheritedContext.clientOnly, deferred = inheritedContext.deferred;
				if (!(clientOnly && deferred) && isNonEmptyArray(selection.directives)) selection.directives.forEach(function(dir) {
					var name = dir.name.value;
					if (name === "client") clientOnly = true;
					if (name === "defer") {
						var args = argumentsObjectFromField(dir, context.variables);
						if (!args || args.if !== false) deferred = true;
					}
				});
				if (isField(selection)) {
					var existing = fieldMap.get(selection);
					if (existing) {
						clientOnly = clientOnly && existing.clientOnly;
						deferred = deferred && existing.deferred;
					}
					fieldMap.set(selection, getContextFlavor(context, clientOnly, deferred));
				} else {
					var fragment = getFragmentFromSelection(selection, context.lookupFragment);
					if (!fragment && selection.kind === Kind.FRAGMENT_SPREAD) throw newInvariantError(14, selection.name.value);
					if (fragment && policies.fragmentMatches(fragment, typename, result, context.variables)) flatten(fragment.selectionSet, getContextFlavor(context, clientOnly, deferred));
				}
			});
		})(selectionSet, context);
		return fieldMap;
	};
	StoreWriter.prototype.applyMerges = function(mergeTree, existing, incoming, context, getStorageArgs) {
		var _a;
		var _this = this;
		if (mergeTree.map.size && !isReference(incoming)) {
			var e_1 = !isArray(incoming) && (isReference(existing) || storeValueIsStoreObject(existing)) ? existing : void 0;
			var i_1 = incoming;
			if (e_1 && !getStorageArgs) getStorageArgs = [isReference(e_1) ? e_1.__ref : e_1];
			var changedFields_1;
			var getValue_1 = function(from, name) {
				return isArray(from) ? typeof name === "number" ? from[name] : void 0 : context.store.getFieldValue(from, String(name));
			};
			mergeTree.map.forEach(function(childTree, storeFieldName) {
				var eVal = getValue_1(e_1, storeFieldName);
				var iVal = getValue_1(i_1, storeFieldName);
				if (void 0 === iVal) return;
				if (getStorageArgs) getStorageArgs.push(storeFieldName);
				var aVal = _this.applyMerges(childTree, eVal, iVal, context, getStorageArgs);
				if (aVal !== iVal) {
					changedFields_1 = changedFields_1 || /* @__PURE__ */ new Map();
					changedFields_1.set(storeFieldName, aVal);
				}
				if (getStorageArgs) invariant$1(getStorageArgs.pop() === storeFieldName);
			});
			if (changedFields_1) {
				incoming = isArray(i_1) ? i_1.slice(0) : __assign({}, i_1);
				changedFields_1.forEach(function(value, name) {
					incoming[name] = value;
				});
			}
		}
		if (mergeTree.info) return this.cache.policies.runMergeFunction(existing, incoming, mergeTree.info, context, getStorageArgs && (_a = context.store).getStorage.apply(_a, getStorageArgs));
		return incoming;
	};
	return StoreWriter;
}();
var emptyMergeTreePool = [];
function getChildMergeTree(_a, name) {
	var map = _a.map;
	if (!map.has(name)) map.set(name, emptyMergeTreePool.pop() || { map: /* @__PURE__ */ new Map() });
	return map.get(name);
}
function mergeMergeTrees(left, right) {
	if (left === right || !right || mergeTreeIsEmpty(right)) return left;
	if (!left || mergeTreeIsEmpty(left)) return right;
	var info = left.info && right.info ? __assign(__assign({}, left.info), right.info) : left.info || right.info;
	var needToMergeMaps = left.map.size && right.map.size;
	var merged = {
		info,
		map: needToMergeMaps ? /* @__PURE__ */ new Map() : left.map.size ? left.map : right.map
	};
	if (needToMergeMaps) {
		var remainingRightKeys_1 = new Set(right.map.keys());
		left.map.forEach(function(leftTree, key) {
			merged.map.set(key, mergeMergeTrees(leftTree, right.map.get(key)));
			remainingRightKeys_1.delete(key);
		});
		remainingRightKeys_1.forEach(function(key) {
			merged.map.set(key, mergeMergeTrees(right.map.get(key), left.map.get(key)));
		});
	}
	return merged;
}
function mergeTreeIsEmpty(tree) {
	return !tree || !(tree.info || tree.map.size);
}
function maybeRecycleChildMergeTree(_a, name) {
	var map = _a.map;
	var childTree = map.get(name);
	if (childTree && mergeTreeIsEmpty(childTree)) {
		emptyMergeTreePool.push(childTree);
		map.delete(name);
	}
}
var warnings = /* @__PURE__ */ new Set();
function warnAboutDataLoss(existingRef, incomingObj, storeFieldName, store) {
	var getChild = function(objOrRef) {
		var child = store.getFieldValue(objOrRef, storeFieldName);
		return typeof child === "object" && child;
	};
	var existing = getChild(existingRef);
	if (!existing) return;
	var incoming = getChild(incomingObj);
	if (!incoming) return;
	if (isReference(existing)) return;
	if (equal(existing, incoming)) return;
	if (Object.keys(existing).every(function(key) {
		return store.getFieldValue(incoming, key) !== void 0;
	})) return;
	var parentType = store.getFieldValue(existingRef, "__typename") || store.getFieldValue(incomingObj, "__typename");
	var fieldName = fieldNameFromStoreName(storeFieldName);
	var typeDotName = "".concat(parentType, ".").concat(fieldName);
	if (warnings.has(typeDotName)) return;
	warnings.add(typeDotName);
	var childTypenames = [];
	if (!isArray(existing) && !isArray(incoming)) [existing, incoming].forEach(function(child) {
		var typename = store.getFieldValue(child, "__typename");
		if (typeof typename === "string" && !childTypenames.includes(typename)) childTypenames.push(typename);
	});
	globalThis.__DEV__ !== false && invariant$1.warn(15, fieldName, parentType, childTypenames.length ? "either ensure all objects of type " + childTypenames.join(" and ") + " have an ID or a custom merge function, or " : "", typeDotName, __assign({}, existing), __assign({}, incoming));
}
//#endregion
//#region node_modules/@apollo/client/cache/inmemory/inMemoryCache.js
var InMemoryCache$1 = function(_super) {
	__extends(InMemoryCache, _super);
	function InMemoryCache(config) {
		if (config === void 0) config = {};
		var _this = _super.call(this) || this;
		_this.watches = /* @__PURE__ */ new Set();
		_this.addTypenameTransform = new DocumentTransform(addTypenameToDocument);
		_this.assumeImmutableResults = true;
		_this.makeVar = makeVar;
		_this.txCount = 0;
		if (globalThis.__DEV__ !== false) {
			warnRemovedOption(config, "addTypename", "InMemoryCache", "Please remove the `addTypename` option when initializing `InMemoryCache`.");
			warnRemovedOption(config, "canonizeResults", "InMemoryCache", "Please remove the `canonizeResults` option when initializing `InMemoryCache`.");
		}
		_this.config = normalizeConfig(config);
		_this.addTypename = !!_this.config.addTypename;
		_this.policies = new Policies({
			cache: _this,
			dataIdFromObject: _this.config.dataIdFromObject,
			possibleTypes: _this.config.possibleTypes,
			typePolicies: _this.config.typePolicies
		});
		_this.init();
		return _this;
	}
	InMemoryCache.prototype.init = function() {
		var rootStore = this.data = new EntityStore.Root({
			policies: this.policies,
			resultCaching: this.config.resultCaching
		});
		this.optimisticData = rootStore.stump;
		this.resetResultCache();
	};
	InMemoryCache.prototype.resetResultCache = function(resetResultIdentities) {
		var _this = this;
		var previousReader = this.storeReader;
		var fragments = this.config.fragments;
		this.addTypenameTransform.resetCache();
		fragments === null || fragments === void 0 || fragments.resetCaches();
		this.storeWriter = new StoreWriter(this, this.storeReader = new StoreReader({
			cache: this,
			addTypename: this.addTypename,
			resultCacheMaxSize: this.config.resultCacheMaxSize,
			canonizeResults: shouldCanonizeResults(this.config),
			canon: resetResultIdentities ? void 0 : previousReader && previousReader.canon,
			fragments
		}), fragments);
		this.maybeBroadcastWatch = wrap(function(c, options) {
			return _this.broadcastWatch(c, options);
		}, {
			max: this.config.resultCacheMaxSize || cacheSizes["inMemoryCache.maybeBroadcastWatch"] || 5e3,
			makeCacheKey: function(c) {
				var store = c.optimistic ? _this.optimisticData : _this.data;
				if (supportsResultCaching(store)) {
					var optimistic = c.optimistic, id = c.id, variables = c.variables;
					return store.makeCacheKey(c.query, c.callback, canonicalStringify({
						optimistic,
						id,
						variables
					}));
				}
			}
		});
		new Set([this.data.group, this.optimisticData.group]).forEach(function(group) {
			return group.resetCaching();
		});
	};
	InMemoryCache.prototype.restore = function(data) {
		this.init();
		if (data) this.data.replace(data);
		return this;
	};
	InMemoryCache.prototype.extract = function(optimistic) {
		if (optimistic === void 0) optimistic = false;
		return (optimistic ? this.optimisticData : this.data).extract();
	};
	InMemoryCache.prototype.read = function(options) {
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.read");
		var _a = options.returnPartialData, returnPartialData = _a === void 0 ? false : _a;
		try {
			return this.storeReader.diffQueryAgainstStore(__assign(__assign({}, options), {
				store: options.optimistic ? this.optimisticData : this.data,
				config: this.config,
				returnPartialData
			})).result || null;
		} catch (e) {
			if (e instanceof MissingFieldError) return null;
			throw e;
		}
	};
	InMemoryCache.prototype.write = function(options) {
		try {
			++this.txCount;
			return this.storeWriter.writeToStore(this.data, options);
		} finally {
			if (!--this.txCount && options.broadcast !== false) this.broadcastWatches();
		}
	};
	InMemoryCache.prototype.modify = function(options) {
		if (hasOwn.call(options, "id") && !options.id) return false;
		var store = options.optimistic ? this.optimisticData : this.data;
		try {
			++this.txCount;
			return store.modify(options.id || "ROOT_QUERY", options.fields);
		} finally {
			if (!--this.txCount && options.broadcast !== false) this.broadcastWatches();
		}
	};
	InMemoryCache.prototype.diff = function(options) {
		if (globalThis.__DEV__ !== false) warnRemovedOption(options, "canonizeResults", "cache.diff");
		return this.storeReader.diffQueryAgainstStore(__assign(__assign({}, options), {
			store: options.optimistic ? this.optimisticData : this.data,
			rootId: options.id || "ROOT_QUERY",
			config: this.config
		}));
	};
	InMemoryCache.prototype.watch = function(watch) {
		var _this = this;
		if (!this.watches.size) recallCache(this);
		this.watches.add(watch);
		if (watch.immediate) this.maybeBroadcastWatch(watch);
		return function() {
			if (_this.watches.delete(watch) && !_this.watches.size) forgetCache(_this);
			_this.maybeBroadcastWatch.forget(watch);
		};
	};
	InMemoryCache.prototype.gc = function(options) {
		if (globalThis.__DEV__ !== false) warnRemovedOption(options || {}, "resetResultIdentities", "cache.gc", "First ensure all usages of `canonizeResults` are removed, then remove this option.");
		canonicalStringify.reset();
		print.reset();
		var ids = this.optimisticData.gc();
		if (options && !this.txCount) {
			if (options.resetResultCache) this.resetResultCache(options.resetResultIdentities);
			else if (options.resetResultIdentities) this.storeReader.resetCanon();
		}
		return ids;
	};
	InMemoryCache.prototype.retain = function(rootId, optimistic) {
		return (optimistic ? this.optimisticData : this.data).retain(rootId);
	};
	InMemoryCache.prototype.release = function(rootId, optimistic) {
		return (optimistic ? this.optimisticData : this.data).release(rootId);
	};
	InMemoryCache.prototype.identify = function(object) {
		if (isReference(object)) return object.__ref;
		try {
			return this.policies.identify(object)[0];
		} catch (e) {
			globalThis.__DEV__ !== false && invariant$1.warn(e);
		}
	};
	InMemoryCache.prototype.evict = function(options) {
		if (!options.id) {
			if (hasOwn.call(options, "id")) return false;
			options = __assign(__assign({}, options), { id: "ROOT_QUERY" });
		}
		try {
			++this.txCount;
			return this.optimisticData.evict(options, this.data);
		} finally {
			if (!--this.txCount && options.broadcast !== false) this.broadcastWatches();
		}
	};
	InMemoryCache.prototype.reset = function(options) {
		var _this = this;
		this.init();
		canonicalStringify.reset();
		if (options && options.discardWatches) {
			this.watches.forEach(function(watch) {
				return _this.maybeBroadcastWatch.forget(watch);
			});
			this.watches.clear();
			forgetCache(this);
		} else this.broadcastWatches();
		return Promise.resolve();
	};
	InMemoryCache.prototype.removeOptimistic = function(idToRemove) {
		var newOptimisticData = this.optimisticData.removeLayer(idToRemove);
		if (newOptimisticData !== this.optimisticData) {
			this.optimisticData = newOptimisticData;
			this.broadcastWatches();
		}
	};
	InMemoryCache.prototype.batch = function(options) {
		var _this = this;
		var update = options.update, _a = options.optimistic, optimistic = _a === void 0 ? true : _a, removeOptimistic = options.removeOptimistic, onWatchUpdated = options.onWatchUpdated;
		var updateResult;
		var perform = function(layer) {
			var _a = _this, data = _a.data, optimisticData = _a.optimisticData;
			++_this.txCount;
			if (layer) _this.data = _this.optimisticData = layer;
			try {
				return updateResult = update(_this);
			} finally {
				--_this.txCount;
				_this.data = data;
				_this.optimisticData = optimisticData;
			}
		};
		var alreadyDirty = /* @__PURE__ */ new Set();
		if (onWatchUpdated && !this.txCount) this.broadcastWatches(__assign(__assign({}, options), { onWatchUpdated: function(watch) {
			alreadyDirty.add(watch);
			return false;
		} }));
		if (typeof optimistic === "string") this.optimisticData = this.optimisticData.addLayer(optimistic, perform);
		else if (optimistic === false) perform(this.data);
		else perform();
		if (typeof removeOptimistic === "string") this.optimisticData = this.optimisticData.removeLayer(removeOptimistic);
		if (onWatchUpdated && alreadyDirty.size) {
			this.broadcastWatches(__assign(__assign({}, options), { onWatchUpdated: function(watch, diff) {
				var result = onWatchUpdated.call(this, watch, diff);
				if (result !== false) alreadyDirty.delete(watch);
				return result;
			} }));
			if (alreadyDirty.size) alreadyDirty.forEach(function(watch) {
				return _this.maybeBroadcastWatch.dirty(watch);
			});
		} else this.broadcastWatches(options);
		return updateResult;
	};
	InMemoryCache.prototype.performTransaction = function(update, optimisticId) {
		return this.batch({
			update,
			optimistic: optimisticId || optimisticId !== null
		});
	};
	InMemoryCache.prototype.transformDocument = function(document) {
		return this.addTypenameToDocument(this.addFragmentsToDocument(document));
	};
	InMemoryCache.prototype.fragmentMatches = function(fragment, typename) {
		return this.policies.fragmentMatches(fragment, typename);
	};
	InMemoryCache.prototype.lookupFragment = function(fragmentName) {
		var _a;
		return ((_a = this.config.fragments) === null || _a === void 0 ? void 0 : _a.lookup(fragmentName)) || null;
	};
	InMemoryCache.prototype.broadcastWatches = function(options) {
		var _this = this;
		if (!this.txCount) this.watches.forEach(function(c) {
			return _this.maybeBroadcastWatch(c, options);
		});
	};
	InMemoryCache.prototype.addFragmentsToDocument = function(document) {
		var fragments = this.config.fragments;
		return fragments ? fragments.transform(document) : document;
	};
	InMemoryCache.prototype.addTypenameToDocument = function(document) {
		if (this.addTypename) return this.addTypenameTransform.transformDocument(document);
		return document;
	};
	InMemoryCache.prototype.broadcastWatch = function(c, options) {
		var _this = this;
		var lastDiff = c.lastDiff;
		var diff = muteDeprecations("canonizeResults", function() {
			return _this.diff(c);
		});
		if (options) {
			if (c.optimistic && typeof options.optimistic === "string") diff.fromOptimisticTransaction = true;
			if (options.onWatchUpdated && options.onWatchUpdated.call(this, c, diff, lastDiff) === false) return;
		}
		if (!lastDiff || !equal(lastDiff.result, diff.result)) c.callback(c.lastDiff = diff, lastDiff);
	};
	return InMemoryCache;
}(ApolloCache);
if (globalThis.__DEV__ !== false) InMemoryCache$1.prototype.getMemoryInternals = getInMemoryCacheMemoryInternals;
//#endregion
//#region node_modules/@apollo/client/core/networkStatus.js
/**
* The current status of a query’s execution in our system.
*/
var NetworkStatus;
(function(NetworkStatus) {
	/**
	* The query has never been run before and the query is now currently running. A query will still
	* have this network status even if a partial data result was returned from the cache, but a
	* query was dispatched anyway.
	*/
	NetworkStatus[NetworkStatus["loading"] = 1] = "loading";
	/**
	* If `setVariables` was called and a query was fired because of that then the network status
	* will be `setVariables` until the result of that query comes back.
	*/
	NetworkStatus[NetworkStatus["setVariables"] = 2] = "setVariables";
	/**
	* Indicates that `fetchMore` was called on this query and that the query created is currently in
	* flight.
	*/
	NetworkStatus[NetworkStatus["fetchMore"] = 3] = "fetchMore";
	/**
	* Similar to the `setVariables` network status. It means that `refetch` was called on a query
	* and the refetch request is currently in flight.
	*/
	NetworkStatus[NetworkStatus["refetch"] = 4] = "refetch";
	/**
	* Indicates that a polling query is currently in flight. So for example if you are polling a
	* query every 10 seconds then the network status will switch to `poll` every 10 seconds whenever
	* a poll request has been sent but not resolved.
	*/
	NetworkStatus[NetworkStatus["poll"] = 6] = "poll";
	/**
	* No request is in flight for this query, and no errors happened. Everything is OK.
	*/
	NetworkStatus[NetworkStatus["ready"] = 7] = "ready";
	/**
	* No request is in flight for this query, but one or more errors were detected.
	*/
	NetworkStatus[NetworkStatus["error"] = 8] = "error";
})(NetworkStatus || (NetworkStatus = {}));
/**
* Returns true if there is currently a network request in flight according to a given network
* status.
*/
function isNetworkRequestInFlight(networkStatus) {
	return networkStatus ? networkStatus < 7 : false;
}
/**
* Returns true if the network request is in ready or error state according to a given network
* status.
*/
function isNetworkRequestSettled(networkStatus) {
	return networkStatus === 7 || networkStatus === 8;
}
//#endregion
//#region node_modules/@apollo/client/core/ObservableQuery.js
var assign = Object.assign, hasOwnProperty$1 = Object.hasOwnProperty;
var ObservableQuery = function(_super) {
	__extends(ObservableQuery, _super);
	function ObservableQuery(_a) {
		var queryManager = _a.queryManager, queryInfo = _a.queryInfo, options = _a.options;
		var _this = this;
		var startedInactive = ObservableQuery.inactiveOnCreation.getValue();
		_this = _super.call(this, function(observer) {
			_this._getOrCreateQuery();
			try {
				var subObserver = observer._subscription._observer;
				if (subObserver && !subObserver.error) subObserver.error = defaultSubscriptionObserverErrorCallback;
			} catch (_a) {}
			var first = !_this.observers.size;
			_this.observers.add(observer);
			var last = _this.last;
			if (last && last.error) observer.error && observer.error(last.error);
			else if (last && last.result) observer.next && observer.next(_this.maskResult(last.result));
			if (first) _this.reobserve().catch(function() {});
			return function() {
				if (_this.observers.delete(observer) && !_this.observers.size) _this.tearDownQuery();
			};
		}) || this;
		_this.observers = /* @__PURE__ */ new Set();
		_this.subscriptions = /* @__PURE__ */ new Set();
		_this.dirty = false;
		_this._getOrCreateQuery = function() {
			if (startedInactive) {
				queryManager["queries"].set(_this.queryId, queryInfo);
				startedInactive = false;
			}
			return _this.queryManager.getOrCreateQuery(_this.queryId);
		};
		_this.queryInfo = queryInfo;
		_this.queryManager = queryManager;
		_this.waitForOwnResult = skipCacheDataFor(options.fetchPolicy);
		_this.isTornDown = false;
		_this.subscribeToMore = _this.subscribeToMore.bind(_this);
		_this.maskResult = _this.maskResult.bind(_this);
		var _b = queryManager.defaultOptions.watchQuery, _d = (_b === void 0 ? {} : _b).fetchPolicy, defaultFetchPolicy = _d === void 0 ? "cache-first" : _d;
		var _e = options.fetchPolicy, fetchPolicy = _e === void 0 ? defaultFetchPolicy : _e, _f = options.initialFetchPolicy, initialFetchPolicy = _f === void 0 ? fetchPolicy === "standby" ? defaultFetchPolicy : fetchPolicy : _f;
		_this.options = __assign(__assign({}, options), {
			initialFetchPolicy,
			fetchPolicy
		});
		_this.queryId = queryInfo.queryId || queryManager.generateQueryId();
		var opDef = getOperationDefinition(_this.query);
		_this.queryName = opDef && opDef.name && opDef.name.value;
		return _this;
	}
	Object.defineProperty(ObservableQuery.prototype, "query", {
		get: function() {
			return this.lastQuery || this.options.query;
		},
		enumerable: false,
		configurable: true
	});
	Object.defineProperty(ObservableQuery.prototype, "variables", {
		/**
		* An object containing the variables that were provided for the query.
		*/
		get: function() {
			return this.options.variables;
		},
		enumerable: false,
		configurable: true
	});
	/**
	* @deprecated `result` will be removed in Apollo Client 4.0.
	*
	* **Recommended now**
	*
	* If you continue to need this functionality, subscribe to `ObservableQuery`
	* to get the first value emitted from the observable, then immediately unsubscribe.
	*
	* **When upgrading**
	*
	* Use RxJS's [`firstResultFrom`](https://rxjs.dev/api/index/function/firstValueFrom) function to mimic this functionality.
	*
	* ```ts
	* const result = await firstValueFrom(from(observableQuery));
	* ```
	*/
	ObservableQuery.prototype.result = function() {
		var _this = this;
		if (globalThis.__DEV__ !== false) warnDeprecated("observableQuery.result", function() {
			globalThis.__DEV__ !== false && invariant$1.warn(23);
		});
		return new Promise(function(resolve, reject) {
			var observer = {
				next: function(result) {
					resolve(result);
					_this.observers.delete(observer);
					if (!_this.observers.size) _this.queryManager.removeQuery(_this.queryId);
					setTimeout(function() {
						subscription.unsubscribe();
					}, 0);
				},
				error: reject
			};
			var subscription = _this.subscribe(observer);
		});
	};
	/** @internal */
	ObservableQuery.prototype.resetDiff = function() {
		this.queryInfo.resetDiff();
	};
	ObservableQuery.prototype.getCurrentFullResult = function(saveAsLastResult) {
		var _this = this;
		if (saveAsLastResult === void 0) saveAsLastResult = true;
		var lastResult = muteDeprecations("getLastResult", function() {
			return _this.getLastResult(true);
		});
		var networkStatus = this.queryInfo.networkStatus || lastResult && lastResult.networkStatus || NetworkStatus.ready;
		var result = __assign(__assign({}, lastResult), {
			loading: isNetworkRequestInFlight(networkStatus),
			networkStatus
		});
		var _a = this.options.fetchPolicy, fetchPolicy = _a === void 0 ? "cache-first" : _a;
		if (skipCacheDataFor(fetchPolicy) || this.queryManager.getDocumentInfo(this.query).hasForcedResolvers) {} else if (this.waitForOwnResult) this.queryInfo["updateWatch"]();
		else {
			var diff = this.queryInfo.getDiff();
			if (diff.complete || this.options.returnPartialData) result.data = diff.result;
			if (equal(result.data, {})) result.data = void 0;
			if (diff.complete) {
				delete result.partial;
				if (diff.complete && result.networkStatus === NetworkStatus.loading && (fetchPolicy === "cache-first" || fetchPolicy === "cache-only")) {
					result.networkStatus = NetworkStatus.ready;
					result.loading = false;
				}
			} else result.partial = true;
			if (result.networkStatus === NetworkStatus.ready && (result.error || result.errors)) result.networkStatus = NetworkStatus.error;
			if (globalThis.__DEV__ !== false && !diff.complete && !this.options.partialRefetch && !result.loading && !result.data && !result.error) logMissingFieldErrors(diff.missing);
		}
		if (saveAsLastResult) this.updateLastResult(result);
		return result;
	};
	ObservableQuery.prototype.getCurrentResult = function(saveAsLastResult) {
		if (saveAsLastResult === void 0) saveAsLastResult = true;
		return this.maskResult(this.getCurrentFullResult(saveAsLastResult));
	};
	ObservableQuery.prototype.isDifferentFromLastResult = function(newResult, variables) {
		if (!this.last) return true;
		var documentInfo = this.queryManager.getDocumentInfo(this.query);
		var dataMasking = this.queryManager.dataMasking;
		var query = dataMasking ? documentInfo.nonReactiveQuery : this.query;
		return (dataMasking || documentInfo.hasNonreactiveDirective ? !equalByQuery(query, this.last.result, newResult, this.variables) : !equal(this.last.result, newResult)) || variables && !equal(this.last.variables, variables);
	};
	ObservableQuery.prototype.getLast = function(key, variablesMustMatch) {
		var last = this.last;
		if (last && last[key] && (!variablesMustMatch || equal(last.variables, this.variables))) return last[key];
	};
	/**
	* @deprecated `getLastResult` will be removed in Apollo Client 4.0. Please
	* discontinue using this method.
	*/
	ObservableQuery.prototype.getLastResult = function(variablesMustMatch) {
		if (globalThis.__DEV__ !== false) warnDeprecated("getLastResult", function() {
			globalThis.__DEV__ !== false && invariant$1.warn(24);
		});
		return this.getLast("result", variablesMustMatch);
	};
	/**
	* @deprecated `getLastError` will be removed in Apollo Client 4.0. Please
	* discontinue using this method.
	*/
	ObservableQuery.prototype.getLastError = function(variablesMustMatch) {
		if (globalThis.__DEV__ !== false) warnDeprecated("getLastError", function() {
			globalThis.__DEV__ !== false && invariant$1.warn(25);
		});
		return this.getLast("error", variablesMustMatch);
	};
	/**
	* @deprecated `resetLastResults` will be removed in Apollo Client 4.0. Please
	* discontinue using this method.
	*/
	ObservableQuery.prototype.resetLastResults = function() {
		if (globalThis.__DEV__ !== false) warnDeprecated("resetLastResults", function() {
			globalThis.__DEV__ !== false && invariant$1.warn(26);
		});
		delete this.last;
		this.isTornDown = false;
	};
	/**
	* @deprecated `resetQueryStoreErrors` will be removed in Apollo Client 4.0.
	* Please discontinue using this method.
	*/
	ObservableQuery.prototype.resetQueryStoreErrors = function() {
		if (globalThis.__DEV__ !== false) globalThis.__DEV__ !== false && invariant$1.warn(27);
		this.queryManager.resetErrors(this.queryId);
	};
	/**
	* Update the variables of this observable query, and fetch the new results.
	* This method should be preferred over `setVariables` in most use cases.
	*
	* @param variables - The new set of variables. If there are missing variables,
	* the previous values of those variables will be used.
	*/
	ObservableQuery.prototype.refetch = function(variables) {
		var _a;
		var reobserveOptions = { pollInterval: 0 };
		if (this.options.fetchPolicy === "no-cache") reobserveOptions.fetchPolicy = "no-cache";
		else reobserveOptions.fetchPolicy = "network-only";
		if (globalThis.__DEV__ !== false && variables && hasOwnProperty$1.call(variables, "variables")) {
			var queryDef = getQueryDefinition(this.query);
			var vars = queryDef.variableDefinitions;
			if (!vars || !vars.some(function(v) {
				return v.variable.name.value === "variables";
			})) globalThis.__DEV__ !== false && invariant$1.warn(28, variables, ((_a = queryDef.name) === null || _a === void 0 ? void 0 : _a.value) || queryDef);
		}
		if (variables && !equal(this.options.variables, variables)) reobserveOptions.variables = this.options.variables = __assign(__assign({}, this.options.variables), variables);
		this.queryInfo.resetLastWrite();
		return this.reobserve(reobserveOptions, NetworkStatus.refetch);
	};
	/**
	* A function that helps you fetch the next set of results for a [paginated list field](https://www.apollographql.com/docs/react/pagination/core-api/).
	*/
	ObservableQuery.prototype.fetchMore = function(fetchMoreOptions) {
		var _this = this;
		var combinedOptions = __assign(__assign({}, fetchMoreOptions.query ? fetchMoreOptions : __assign(__assign(__assign(__assign({}, this.options), { query: this.options.query }), fetchMoreOptions), { variables: __assign(__assign({}, this.options.variables), fetchMoreOptions.variables) })), { fetchPolicy: "no-cache" });
		combinedOptions.query = this.transformDocument(combinedOptions.query);
		var qid = this.queryManager.generateQueryId();
		this.lastQuery = fetchMoreOptions.query ? this.transformDocument(this.options.query) : combinedOptions.query;
		var queryInfo = this.queryInfo;
		var originalNetworkStatus = queryInfo.networkStatus;
		queryInfo.networkStatus = NetworkStatus.fetchMore;
		if (combinedOptions.notifyOnNetworkStatusChange) this.observe();
		var updatedQuerySet = /* @__PURE__ */ new Set();
		var updateQuery = fetchMoreOptions === null || fetchMoreOptions === void 0 ? void 0 : fetchMoreOptions.updateQuery;
		var isCached = this.options.fetchPolicy !== "no-cache";
		if (!isCached) invariant$1(updateQuery, 29);
		return this.queryManager.fetchQuery(qid, combinedOptions, NetworkStatus.fetchMore).then(function(fetchMoreResult) {
			_this.queryManager.removeQuery(qid);
			if (queryInfo.networkStatus === NetworkStatus.fetchMore) queryInfo.networkStatus = originalNetworkStatus;
			if (isCached) _this.queryManager.cache.batch({
				update: function(cache) {
					var updateQuery = fetchMoreOptions.updateQuery;
					if (updateQuery) cache.updateQuery({
						query: _this.query,
						variables: _this.variables,
						returnPartialData: true,
						optimistic: false
					}, function(previous) {
						return updateQuery(previous, {
							fetchMoreResult: fetchMoreResult.data,
							variables: combinedOptions.variables
						});
					});
					else cache.writeQuery({
						query: combinedOptions.query,
						variables: combinedOptions.variables,
						data: fetchMoreResult.data
					});
				},
				onWatchUpdated: function(watch) {
					updatedQuerySet.add(watch.query);
				}
			});
			else {
				var lastResult = _this.getLast("result");
				var data = updateQuery(lastResult.data, {
					fetchMoreResult: fetchMoreResult.data,
					variables: combinedOptions.variables
				});
				_this.reportResult(__assign(__assign({}, lastResult), {
					networkStatus: originalNetworkStatus,
					loading: isNetworkRequestInFlight(originalNetworkStatus),
					data
				}), _this.variables);
			}
			return _this.maskResult(fetchMoreResult);
		}).finally(function() {
			if (isCached && !updatedQuerySet.has(_this.query)) _this.reobserveCacheFirst();
		});
	};
	/**
	* A function that enables you to execute a [subscription](https://www.apollographql.com/docs/react/data/subscriptions/), usually to subscribe to specific fields that were included in the query.
	*
	* This function returns _another_ function that you can call to terminate the subscription.
	*/
	ObservableQuery.prototype.subscribeToMore = function(options) {
		var _this = this;
		var subscription = this.queryManager.startGraphQLSubscription({
			query: options.document,
			variables: options.variables,
			context: options.context
		}).subscribe({
			next: function(subscriptionData) {
				var updateQuery = options.updateQuery;
				if (updateQuery) _this.updateQuery(function(previous, updateOptions) {
					return updateQuery(previous, __assign({ subscriptionData }, updateOptions));
				});
			},
			error: function(err) {
				if (options.onError) {
					options.onError(err);
					return;
				}
				globalThis.__DEV__ !== false && invariant$1.error(30, err);
			}
		});
		this.subscriptions.add(subscription);
		return function() {
			if (_this.subscriptions.delete(subscription)) subscription.unsubscribe();
		};
	};
	/**
	* @deprecated `setOptions` will be removed in Apollo Client 4.0. Please use
	* `observableQuery.reobserve(newOptions)` instead.
	*/
	ObservableQuery.prototype.setOptions = function(newOptions) {
		if (globalThis.__DEV__ !== false) {
			warnRemovedOption(newOptions, "canonizeResults", "setOptions");
			warnDeprecated("setOptions", function() {
				globalThis.__DEV__ !== false && invariant$1.warn(31);
			});
		}
		return this.reobserve(newOptions);
	};
	ObservableQuery.prototype.silentSetOptions = function(newOptions) {
		var mergedOptions = compact(this.options, newOptions || {});
		assign(this.options, mergedOptions);
	};
	/**
	* Update the variables of this observable query, and fetch the new results
	* if they've changed. Most users should prefer `refetch` instead of
	* `setVariables` in order to to be properly notified of results even when
	* they come from the cache.
	*
	* Note: the `next` callback will *not* fire if the variables have not changed
	* or if the result is coming from cache.
	*
	* Note: the promise will return the old results immediately if the variables
	* have not changed.
	*
	* Note: the promise will return null immediately if the query is not active
	* (there are no subscribers).
	*
	* @param variables - The new set of variables. If there are missing variables,
	* the previous values of those variables will be used.
	*/
	ObservableQuery.prototype.setVariables = function(variables) {
		var _this = this;
		if (equal(this.variables, variables)) return this.observers.size ? muteDeprecations("observableQuery.result", function() {
			return _this.result();
		}) : Promise.resolve();
		this.options.variables = variables;
		if (!this.observers.size) return Promise.resolve();
		return this.reobserve({
			fetchPolicy: this.options.initialFetchPolicy,
			variables
		}, NetworkStatus.setVariables);
	};
	/**
	* A function that enables you to update the query's cached result without executing a followup GraphQL operation.
	*
	* See [using updateQuery and updateFragment](https://www.apollographql.com/docs/react/caching/cache-interaction/#using-updatequery-and-updatefragment) for additional information.
	*/
	ObservableQuery.prototype.updateQuery = function(mapFn) {
		var queryManager = this.queryManager;
		var _a = queryManager.cache.diff({
			query: this.options.query,
			variables: this.variables,
			returnPartialData: true,
			optimistic: false
		}), result = _a.result, complete = _a.complete;
		var newResult = mapFn(result, {
			variables: this.variables,
			complete: !!complete,
			previousData: result
		});
		if (newResult) {
			queryManager.cache.writeQuery({
				query: this.options.query,
				data: newResult,
				variables: this.variables
			});
			queryManager.broadcastQueries();
		}
	};
	/**
	* A function that instructs the query to begin re-executing at a specified interval (in milliseconds).
	*/
	ObservableQuery.prototype.startPolling = function(pollInterval) {
		this.options.pollInterval = pollInterval;
		this.updatePolling();
	};
	/**
	* A function that instructs the query to stop polling after a previous call to `startPolling`.
	*/
	ObservableQuery.prototype.stopPolling = function() {
		this.options.pollInterval = 0;
		this.updatePolling();
	};
	ObservableQuery.prototype.applyNextFetchPolicy = function(reason, options) {
		if (options.nextFetchPolicy) {
			var _a = options.fetchPolicy, fetchPolicy = _a === void 0 ? "cache-first" : _a, _b = options.initialFetchPolicy, initialFetchPolicy = _b === void 0 ? fetchPolicy : _b;
			if (fetchPolicy === "standby") {} else if (typeof options.nextFetchPolicy === "function") options.fetchPolicy = options.nextFetchPolicy(fetchPolicy, {
				reason,
				options,
				observable: this,
				initialFetchPolicy
			});
			else if (reason === "variables-changed") options.fetchPolicy = initialFetchPolicy;
			else options.fetchPolicy = options.nextFetchPolicy;
		}
		return options.fetchPolicy;
	};
	ObservableQuery.prototype.fetch = function(options, newNetworkStatus, query) {
		var queryInfo = this._getOrCreateQuery();
		queryInfo.setObservableQuery(this);
		return this.queryManager["fetchConcastWithInfo"](queryInfo, options, newNetworkStatus, query);
	};
	ObservableQuery.prototype.updatePolling = function() {
		var _this = this;
		if (this.queryManager.ssrMode) return;
		var _a = this, pollingInfo = _a.pollingInfo, pollInterval = _a.options.pollInterval;
		if (!pollInterval || !this.hasObservers()) {
			if (pollingInfo) {
				clearTimeout(pollingInfo.timeout);
				delete this.pollingInfo;
			}
			return;
		}
		if (pollingInfo && pollingInfo.interval === pollInterval) return;
		invariant$1(pollInterval, 32);
		var info = pollingInfo || (this.pollingInfo = {});
		info.interval = pollInterval;
		var maybeFetch = function() {
			var _a, _b;
			if (_this.pollingInfo) if (!isNetworkRequestInFlight(_this.queryInfo.networkStatus) && !((_b = (_a = _this.options).skipPollAttempt) === null || _b === void 0 ? void 0 : _b.call(_a))) _this.reobserve({ fetchPolicy: _this.options.initialFetchPolicy === "no-cache" ? "no-cache" : "network-only" }, NetworkStatus.poll).then(poll, poll);
			else poll();
		};
		var poll = function() {
			var info = _this.pollingInfo;
			if (info) {
				clearTimeout(info.timeout);
				info.timeout = setTimeout(maybeFetch, info.interval);
			}
		};
		poll();
	};
	ObservableQuery.prototype.updateLastResult = function(newResult, variables) {
		var _this = this;
		if (variables === void 0) variables = this.variables;
		var error = muteDeprecations("getLastError", function() {
			return _this.getLastError();
		});
		if (error && this.last && !equal(variables, this.last.variables)) error = void 0;
		return this.last = __assign({
			result: this.queryManager.assumeImmutableResults ? newResult : cloneDeep(newResult),
			variables
		}, error ? { error } : null);
	};
	ObservableQuery.prototype.reobserveAsConcast = function(newOptions, newNetworkStatus) {
		var _this = this;
		this.isTornDown = false;
		var useDisposableConcast = newNetworkStatus === NetworkStatus.refetch || newNetworkStatus === NetworkStatus.fetchMore || newNetworkStatus === NetworkStatus.poll;
		var oldVariables = this.options.variables;
		var oldFetchPolicy = this.options.fetchPolicy;
		var mergedOptions = compact(this.options, newOptions || {});
		var options = useDisposableConcast ? mergedOptions : assign(this.options, mergedOptions);
		var query = this.transformDocument(options.query);
		this.lastQuery = query;
		if (!useDisposableConcast) {
			this.updatePolling();
			if (newOptions && newOptions.variables && !equal(newOptions.variables, oldVariables) && options.fetchPolicy !== "standby" && (options.fetchPolicy === oldFetchPolicy || typeof options.nextFetchPolicy === "function")) {
				this.applyNextFetchPolicy("variables-changed", options);
				if (newNetworkStatus === void 0) newNetworkStatus = NetworkStatus.setVariables;
			}
		}
		this.waitForOwnResult && (this.waitForOwnResult = skipCacheDataFor(options.fetchPolicy));
		var finishWaitingForOwnResult = function() {
			if (_this.concast === concast) _this.waitForOwnResult = false;
		};
		var variables = options.variables && __assign({}, options.variables);
		var _a = this.fetch(options, newNetworkStatus, query), concast = _a.concast, fromLink = _a.fromLink;
		var observer = {
			next: function(result) {
				if (equal(_this.variables, variables)) {
					finishWaitingForOwnResult();
					_this.reportResult(result, variables);
				}
			},
			error: function(error) {
				if (equal(_this.variables, variables)) {
					if (!isApolloError(error)) error = new ApolloError({ networkError: error });
					finishWaitingForOwnResult();
					_this.reportError(error, variables);
				}
			}
		};
		if (!useDisposableConcast && (fromLink || !this.concast)) {
			if (this.concast && this.observer) this.concast.removeObserver(this.observer);
			this.concast = concast;
			this.observer = observer;
		}
		concast.addObserver(observer);
		return concast;
	};
	ObservableQuery.prototype.reobserve = function(newOptions, newNetworkStatus) {
		return preventUnhandledRejection(this.reobserveAsConcast(newOptions, newNetworkStatus).promise.then(this.maskResult));
	};
	ObservableQuery.prototype.resubscribeAfterError = function() {
		var _this = this;
		var args = [];
		for (var _i = 0; _i < arguments.length; _i++) args[_i] = arguments[_i];
		var last = this.last;
		muteDeprecations("resetLastResults", function() {
			return _this.resetLastResults();
		});
		var subscription = this.subscribe.apply(this, args);
		this.last = last;
		return subscription;
	};
	ObservableQuery.prototype.observe = function() {
		this.reportResult(this.getCurrentFullResult(false), this.variables);
	};
	ObservableQuery.prototype.reportResult = function(result, variables) {
		var _this = this;
		var lastError = muteDeprecations("getLastError", function() {
			return _this.getLastError();
		});
		var isDifferent = this.isDifferentFromLastResult(result, variables);
		if (lastError || !result.partial || this.options.returnPartialData) this.updateLastResult(result, variables);
		if (lastError || isDifferent) iterateObserversSafely(this.observers, "next", this.maskResult(result));
	};
	ObservableQuery.prototype.reportError = function(error, variables) {
		var _this = this;
		var errorResult = __assign(__assign({}, muteDeprecations("getLastResult", function() {
			return _this.getLastResult();
		})), {
			error,
			errors: error.graphQLErrors,
			networkStatus: NetworkStatus.error,
			loading: false
		});
		this.updateLastResult(errorResult, variables);
		iterateObserversSafely(this.observers, "error", this.last.error = error);
	};
	ObservableQuery.prototype.hasObservers = function() {
		return this.observers.size > 0;
	};
	ObservableQuery.prototype.tearDownQuery = function() {
		if (this.isTornDown) return;
		if (this.concast && this.observer) {
			this.concast.removeObserver(this.observer);
			delete this.concast;
			delete this.observer;
		}
		this.stopPolling();
		this.subscriptions.forEach(function(sub) {
			return sub.unsubscribe();
		});
		this.subscriptions.clear();
		this.queryManager.stopQuery(this.queryId);
		this.observers.clear();
		this.isTornDown = true;
	};
	ObservableQuery.prototype.transformDocument = function(document) {
		return this.queryManager.transform(document);
	};
	ObservableQuery.prototype.maskResult = function(result) {
		return result && "data" in result ? __assign(__assign({}, result), { data: this.queryManager.maskOperation({
			document: this.query,
			data: result.data,
			fetchPolicy: this.options.fetchPolicy,
			id: this.queryId
		}) }) : result;
	};
	/** @internal */
	ObservableQuery.prototype.resetNotifications = function() {
		this.cancelNotifyTimeout();
		this.dirty = false;
	};
	ObservableQuery.prototype.cancelNotifyTimeout = function() {
		if (this.notifyTimeout) {
			clearTimeout(this.notifyTimeout);
			this.notifyTimeout = void 0;
		}
	};
	/** @internal */
	ObservableQuery.prototype.scheduleNotify = function() {
		var _this = this;
		if (this.dirty) return;
		this.dirty = true;
		if (!this.notifyTimeout) this.notifyTimeout = setTimeout(function() {
			return _this.notify();
		}, 0);
	};
	/** @internal */
	ObservableQuery.prototype.notify = function() {
		this.cancelNotifyTimeout();
		if (this.dirty) {
			if (this.options.fetchPolicy == "cache-only" || this.options.fetchPolicy == "cache-and-network" || !isNetworkRequestInFlight(this.queryInfo.networkStatus)) if (this.queryInfo.getDiff().fromOptimisticTransaction) this.observe();
			else this.reobserveCacheFirst();
		}
		this.dirty = false;
	};
	ObservableQuery.prototype.reobserveCacheFirst = function() {
		var _a = this.options, fetchPolicy = _a.fetchPolicy, nextFetchPolicy = _a.nextFetchPolicy;
		if (fetchPolicy === "cache-and-network" || fetchPolicy === "network-only") return this.reobserve({
			fetchPolicy: "cache-first",
			nextFetchPolicy: function(currentFetchPolicy, context) {
				this.nextFetchPolicy = nextFetchPolicy;
				if (typeof this.nextFetchPolicy === "function") return this.nextFetchPolicy(currentFetchPolicy, context);
				return fetchPolicy;
			}
		});
		return this.reobserve();
	};
	/**
	* @internal
	* A slot used by the `useQuery` hook to indicate that `client.watchQuery`
	* should not register the query immediately, but instead wait for the query to
	* be started registered with the `QueryManager` when `useSyncExternalStore`
	* actively subscribes to it.
	*/
	ObservableQuery.inactiveOnCreation = new Slot();
	return ObservableQuery;
}(Observable);
fixObservableSubclass(ObservableQuery);
function defaultSubscriptionObserverErrorCallback(error) {
	globalThis.__DEV__ !== false && invariant$1.error(33, error.message, error.stack);
}
function logMissingFieldErrors(missing) {
	if (globalThis.__DEV__ !== false && missing) globalThis.__DEV__ !== false && invariant$1.debug(34, missing);
}
function skipCacheDataFor(fetchPolicy) {
	return fetchPolicy === "network-only" || fetchPolicy === "no-cache" || fetchPolicy === "standby";
}
//#endregion
//#region node_modules/@apollo/client/core/QueryInfo.js
var destructiveMethodCounts = new (canUseWeakMap ? WeakMap : Map)();
function wrapDestructiveCacheMethod(cache, methodName) {
	var original = cache[methodName];
	if (typeof original === "function") cache[methodName] = function() {
		destructiveMethodCounts.set(cache, (destructiveMethodCounts.get(cache) + 1) % 0x38d7ea4c68000);
		return original.apply(this, arguments);
	};
}
var QueryInfo = function() {
	function QueryInfo(queryManager, queryId) {
		if (queryId === void 0) queryId = queryManager.generateQueryId();
		this.queryId = queryId;
		this.document = null;
		this.lastRequestId = 1;
		this.stopped = false;
		this.observableQuery = null;
		var cache = this.cache = queryManager.cache;
		if (!destructiveMethodCounts.has(cache)) {
			destructiveMethodCounts.set(cache, 0);
			wrapDestructiveCacheMethod(cache, "evict");
			wrapDestructiveCacheMethod(cache, "modify");
			wrapDestructiveCacheMethod(cache, "reset");
		}
	}
	QueryInfo.prototype.init = function(query) {
		var networkStatus = query.networkStatus || NetworkStatus.loading;
		if (this.variables && this.networkStatus !== NetworkStatus.loading && !equal(this.variables, query.variables)) networkStatus = NetworkStatus.setVariables;
		if (!equal(query.variables, this.variables)) {
			this.lastDiff = void 0;
			this.cancel();
		}
		Object.assign(this, {
			document: query.document,
			variables: query.variables,
			networkError: null,
			graphQLErrors: this.graphQLErrors || [],
			networkStatus
		});
		if (query.observableQuery) this.setObservableQuery(query.observableQuery);
		if (query.lastRequestId) this.lastRequestId = query.lastRequestId;
		return this;
	};
	QueryInfo.prototype.resetDiff = function() {
		this.lastDiff = void 0;
	};
	QueryInfo.prototype.getDiff = function() {
		var _this = this;
		var options = this.getDiffOptions();
		if (this.lastDiff && equal(options, this.lastDiff.options)) return this.lastDiff.diff;
		this.updateWatch(this.variables);
		var oq = this.observableQuery;
		if (oq && oq.options.fetchPolicy === "no-cache") return { complete: false };
		var diff = muteDeprecations("canonizeResults", function() {
			return _this.cache.diff(options);
		});
		this.updateLastDiff(diff, options);
		return diff;
	};
	QueryInfo.prototype.updateLastDiff = function(diff, options) {
		this.lastDiff = diff ? {
			diff,
			options: options || this.getDiffOptions()
		} : void 0;
	};
	QueryInfo.prototype.getDiffOptions = function(variables) {
		var _a;
		if (variables === void 0) variables = this.variables;
		return {
			query: this.document,
			variables,
			returnPartialData: true,
			optimistic: true,
			canonizeResults: (_a = this.observableQuery) === null || _a === void 0 ? void 0 : _a.options.canonizeResults
		};
	};
	QueryInfo.prototype.setDiff = function(diff) {
		var _this = this;
		var _a;
		var oldDiff = this.lastDiff && this.lastDiff.diff;
		if (diff && !diff.complete && muteDeprecations("getLastError", function() {
			var _a;
			return (_a = _this.observableQuery) === null || _a === void 0 ? void 0 : _a.getLastError();
		})) return;
		this.updateLastDiff(diff);
		if (!equal(oldDiff && oldDiff.result, diff && diff.result)) (_a = this.observableQuery) === null || _a === void 0 || _a["scheduleNotify"]();
	};
	QueryInfo.prototype.setObservableQuery = function(oq) {
		if (oq === this.observableQuery) return;
		this.observableQuery = oq;
		if (oq) oq["queryInfo"] = this;
	};
	QueryInfo.prototype.stop = function() {
		var _a;
		if (!this.stopped) {
			this.stopped = true;
			(_a = this.observableQuery) === null || _a === void 0 || _a["resetNotifications"]();
			this.cancel();
			var oq = this.observableQuery;
			if (oq) oq.stopPolling();
		}
	};
	QueryInfo.prototype.cancel = function() {
		var _a;
		(_a = this.cancelWatch) === null || _a === void 0 || _a.call(this);
		this.cancelWatch = void 0;
	};
	QueryInfo.prototype.updateWatch = function(variables) {
		var _this = this;
		if (variables === void 0) variables = this.variables;
		var oq = this.observableQuery;
		if (oq && oq.options.fetchPolicy === "no-cache") return;
		var watchOptions = __assign(__assign({}, this.getDiffOptions(variables)), {
			watcher: this,
			callback: function(diff) {
				return _this.setDiff(diff);
			}
		});
		if (!this.lastWatch || !equal(watchOptions, this.lastWatch)) {
			this.cancel();
			this.cancelWatch = this.cache.watch(this.lastWatch = watchOptions);
		}
	};
	QueryInfo.prototype.resetLastWrite = function() {
		this.lastWrite = void 0;
	};
	QueryInfo.prototype.shouldWrite = function(result, variables) {
		var lastWrite = this.lastWrite;
		return !(lastWrite && lastWrite.dmCount === destructiveMethodCounts.get(this.cache) && equal(variables, lastWrite.variables) && equal(result.data, lastWrite.result.data));
	};
	QueryInfo.prototype.markResult = function(result, document, options, cacheWriteBehavior) {
		var _this = this;
		var _a;
		var merger = new DeepMerger();
		var graphQLErrors = isNonEmptyArray(result.errors) ? result.errors.slice(0) : [];
		(_a = this.observableQuery) === null || _a === void 0 || _a["resetNotifications"]();
		if ("incremental" in result && isNonEmptyArray(result.incremental)) result.data = mergeIncrementalData(this.getDiff().result, result);
		else if ("hasNext" in result && result.hasNext) {
			var diff = this.getDiff();
			result.data = merger.merge(diff.result, result.data);
		}
		this.graphQLErrors = graphQLErrors;
		if (options.fetchPolicy === "no-cache") this.updateLastDiff({
			result: result.data,
			complete: true
		}, this.getDiffOptions(options.variables));
		else if (cacheWriteBehavior !== 0) if (shouldWriteResult(result, options.errorPolicy)) this.cache.performTransaction(function(cache) {
			if (_this.shouldWrite(result, options.variables)) {
				cache.writeQuery({
					query: document,
					data: result.data,
					variables: options.variables,
					overwrite: cacheWriteBehavior === 1
				});
				_this.lastWrite = {
					result,
					variables: options.variables,
					dmCount: destructiveMethodCounts.get(_this.cache)
				};
			} else if (_this.lastDiff && _this.lastDiff.diff.complete) {
				result.data = _this.lastDiff.diff.result;
				return;
			}
			var diffOptions = _this.getDiffOptions(options.variables);
			var diff = muteDeprecations("canonizeResults", function() {
				return cache.diff(diffOptions);
			});
			if (!_this.stopped && equal(_this.variables, options.variables)) _this.updateWatch(options.variables);
			_this.updateLastDiff(diff, diffOptions);
			if (diff.complete) result.data = diff.result;
		});
		else this.lastWrite = void 0;
	};
	QueryInfo.prototype.markReady = function() {
		this.networkError = null;
		return this.networkStatus = NetworkStatus.ready;
	};
	QueryInfo.prototype.markError = function(error) {
		var _a;
		this.networkStatus = NetworkStatus.error;
		this.lastWrite = void 0;
		(_a = this.observableQuery) === null || _a === void 0 || _a["resetNotifications"]();
		if (error.graphQLErrors) this.graphQLErrors = error.graphQLErrors;
		if (error.networkError) this.networkError = error.networkError;
		return error;
	};
	return QueryInfo;
}();
function shouldWriteResult(result, errorPolicy) {
	if (errorPolicy === void 0) errorPolicy = "none";
	var ignoreErrors = errorPolicy === "ignore" || errorPolicy === "all";
	var writeWithErrors = !graphQLResultHasError(result);
	if (!writeWithErrors && ignoreErrors && result.data) writeWithErrors = true;
	return writeWithErrors;
}
//#endregion
//#region node_modules/@apollo/client/core/QueryManager.js
var hasOwnProperty = Object.prototype.hasOwnProperty;
var IGNORE = Object.create(null);
var QueryManager = function() {
	function QueryManager(options) {
		var _this = this;
		this.clientAwareness = {};
		this.queries = /* @__PURE__ */ new Map();
		this.fetchCancelFns = /* @__PURE__ */ new Map();
		this.transformCache = new AutoCleanedWeakCache(cacheSizes["queryManager.getDocumentInfo"] || 2e3);
		this.queryIdCounter = 1;
		this.requestIdCounter = 1;
		this.mutationIdCounter = 1;
		this.inFlightLinkObservables = new Trie(false);
		this.noCacheWarningsByQueryId = /* @__PURE__ */ new Set();
		var defaultDocumentTransform = new DocumentTransform(function(document) {
			return _this.cache.transformDocument(document);
		}, { cache: false });
		this.cache = options.cache;
		this.link = options.link;
		this.defaultOptions = options.defaultOptions;
		this.queryDeduplication = options.queryDeduplication;
		this.clientAwareness = options.clientAwareness;
		this.localState = options.localState;
		this.ssrMode = options.ssrMode;
		this.assumeImmutableResults = options.assumeImmutableResults;
		this.dataMasking = options.dataMasking;
		var documentTransform = options.documentTransform;
		this.documentTransform = documentTransform ? defaultDocumentTransform.concat(documentTransform).concat(defaultDocumentTransform) : defaultDocumentTransform;
		this.defaultContext = options.defaultContext || Object.create(null);
		if (this.onBroadcast = options.onBroadcast) this.mutationStore = Object.create(null);
	}
	/**
	* Call this method to terminate any active query processes, making it safe
	* to dispose of this QueryManager instance.
	*/
	QueryManager.prototype.stop = function() {
		var _this = this;
		this.queries.forEach(function(_info, queryId) {
			_this.stopQueryNoBroadcast(queryId);
		});
		this.cancelPendingFetches(newInvariantError(35));
	};
	QueryManager.prototype.cancelPendingFetches = function(error) {
		this.fetchCancelFns.forEach(function(cancel) {
			return cancel(error);
		});
		this.fetchCancelFns.clear();
	};
	QueryManager.prototype.mutate = function(_a) {
		return __awaiter(this, arguments, void 0, function(_b) {
			var mutationId, hasClientExports, mutationStoreValue, isOptimistic, self;
			var _c, _d;
			var mutation = _b.mutation, variables = _b.variables, optimisticResponse = _b.optimisticResponse, updateQueries = _b.updateQueries, _e = _b.refetchQueries, refetchQueries = _e === void 0 ? [] : _e, _f = _b.awaitRefetchQueries, awaitRefetchQueries = _f === void 0 ? false : _f, updateWithProxyFn = _b.update, onQueryUpdated = _b.onQueryUpdated, _g = _b.fetchPolicy, fetchPolicy = _g === void 0 ? ((_c = this.defaultOptions.mutate) === null || _c === void 0 ? void 0 : _c.fetchPolicy) || "network-only" : _g, _h = _b.errorPolicy, errorPolicy = _h === void 0 ? ((_d = this.defaultOptions.mutate) === null || _d === void 0 ? void 0 : _d.errorPolicy) || "none" : _h, keepRootFields = _b.keepRootFields, context = _b.context;
			return __generator(this, function(_j) {
				switch (_j.label) {
					case 0:
						invariant$1(mutation, 36);
						invariant$1(fetchPolicy === "network-only" || fetchPolicy === "no-cache", 37);
						mutationId = this.generateMutationId();
						mutation = this.cache.transformForLink(this.transform(mutation));
						hasClientExports = this.getDocumentInfo(mutation).hasClientExports;
						variables = this.getVariables(mutation, variables);
						if (!hasClientExports) return [3, 2];
						return [4, this.localState.addExportedVariables(mutation, variables, context)];
					case 1:
						variables = _j.sent();
						_j.label = 2;
					case 2:
						mutationStoreValue = this.mutationStore && (this.mutationStore[mutationId] = {
							mutation,
							variables,
							loading: true,
							error: null
						});
						isOptimistic = optimisticResponse && this.markMutationOptimistic(optimisticResponse, {
							mutationId,
							document: mutation,
							variables,
							fetchPolicy,
							errorPolicy,
							context,
							updateQueries,
							update: updateWithProxyFn,
							keepRootFields
						});
						this.broadcastQueries();
						self = this;
						return [2, new Promise(function(resolve, reject) {
							return asyncMap(self.getObservableFromLink(mutation, __assign(__assign({}, context), { optimisticResponse: isOptimistic ? optimisticResponse : void 0 }), variables, {}, false), function(result) {
								if (graphQLResultHasError(result) && errorPolicy === "none") throw new ApolloError({ graphQLErrors: getGraphQLErrorsFromResult(result) });
								if (mutationStoreValue) {
									mutationStoreValue.loading = false;
									mutationStoreValue.error = null;
								}
								var storeResult = __assign({}, result);
								if (typeof refetchQueries === "function") refetchQueries = refetchQueries(storeResult);
								if (errorPolicy === "ignore" && graphQLResultHasError(storeResult)) delete storeResult.errors;
								return self.markMutationResult({
									mutationId,
									result: storeResult,
									document: mutation,
									variables,
									fetchPolicy,
									errorPolicy,
									context,
									update: updateWithProxyFn,
									updateQueries,
									awaitRefetchQueries,
									refetchQueries,
									removeOptimistic: isOptimistic ? mutationId : void 0,
									onQueryUpdated,
									keepRootFields
								});
							}).subscribe({
								next: function(storeResult) {
									self.broadcastQueries();
									if (!("hasNext" in storeResult) || storeResult.hasNext === false) resolve(__assign(__assign({}, storeResult), { data: self.maskOperation({
										document: mutation,
										data: storeResult.data,
										fetchPolicy,
										id: mutationId
									}) }));
								},
								error: function(err) {
									if (mutationStoreValue) {
										mutationStoreValue.loading = false;
										mutationStoreValue.error = err;
									}
									if (isOptimistic) self.cache.removeOptimistic(mutationId);
									self.broadcastQueries();
									reject(err instanceof ApolloError ? err : new ApolloError({ networkError: err }));
								}
							});
						})];
				}
			});
		});
	};
	QueryManager.prototype.markMutationResult = function(mutation, cache) {
		var _this = this;
		if (cache === void 0) cache = this.cache;
		var result = mutation.result;
		var cacheWrites = [];
		var skipCache = mutation.fetchPolicy === "no-cache";
		if (!skipCache && shouldWriteResult(result, mutation.errorPolicy)) {
			if (!isExecutionPatchIncrementalResult(result)) cacheWrites.push({
				result: result.data,
				dataId: "ROOT_MUTATION",
				query: mutation.document,
				variables: mutation.variables
			});
			if (isExecutionPatchIncrementalResult(result) && isNonEmptyArray(result.incremental)) {
				var diff = cache.diff({
					id: "ROOT_MUTATION",
					query: this.getDocumentInfo(mutation.document).asQuery,
					variables: mutation.variables,
					optimistic: false,
					returnPartialData: true
				});
				var mergedData = void 0;
				if (diff.result) mergedData = mergeIncrementalData(diff.result, result);
				if (typeof mergedData !== "undefined") {
					result.data = mergedData;
					cacheWrites.push({
						result: mergedData,
						dataId: "ROOT_MUTATION",
						query: mutation.document,
						variables: mutation.variables
					});
				}
			}
			var updateQueries_1 = mutation.updateQueries;
			if (updateQueries_1) this.queries.forEach(function(_a, queryId) {
				var observableQuery = _a.observableQuery;
				var queryName = observableQuery && observableQuery.queryName;
				if (!queryName || !hasOwnProperty.call(updateQueries_1, queryName)) return;
				var updater = updateQueries_1[queryName];
				var _b = _this.queries.get(queryId), document = _b.document, variables = _b.variables;
				var _c = cache.diff({
					query: document,
					variables,
					returnPartialData: true,
					optimistic: false
				}), currentQueryResult = _c.result;
				if (_c.complete && currentQueryResult) {
					var nextQueryResult = updater(currentQueryResult, {
						mutationResult: result,
						queryName: document && getOperationName(document) || void 0,
						queryVariables: variables
					});
					if (nextQueryResult) cacheWrites.push({
						result: nextQueryResult,
						dataId: "ROOT_QUERY",
						query: document,
						variables
					});
				}
			});
		}
		if (cacheWrites.length > 0 || (mutation.refetchQueries || "").length > 0 || mutation.update || mutation.onQueryUpdated || mutation.removeOptimistic) {
			var results_1 = [];
			this.refetchQueries({
				updateCache: function(cache) {
					if (!skipCache) cacheWrites.forEach(function(write) {
						return cache.write(write);
					});
					var update = mutation.update;
					var isFinalResult = !isExecutionPatchResult(result) || isExecutionPatchIncrementalResult(result) && !result.hasNext;
					if (update) {
						if (!skipCache) {
							var diff = cache.diff({
								id: "ROOT_MUTATION",
								query: _this.getDocumentInfo(mutation.document).asQuery,
								variables: mutation.variables,
								optimistic: false,
								returnPartialData: true
							});
							if (diff.complete) {
								result = __assign(__assign({}, result), { data: diff.result });
								if ("incremental" in result) delete result.incremental;
								if ("hasNext" in result) delete result.hasNext;
							}
						}
						if (isFinalResult) update(cache, result, {
							context: mutation.context,
							variables: mutation.variables
						});
					}
					if (!skipCache && !mutation.keepRootFields && isFinalResult) cache.modify({
						id: "ROOT_MUTATION",
						fields: function(value, _a) {
							var fieldName = _a.fieldName, DELETE = _a.DELETE;
							return fieldName === "__typename" ? value : DELETE;
						}
					});
				},
				include: mutation.refetchQueries,
				optimistic: false,
				removeOptimistic: mutation.removeOptimistic,
				onQueryUpdated: mutation.onQueryUpdated || null
			}).forEach(function(result) {
				return results_1.push(result);
			});
			if (mutation.awaitRefetchQueries || mutation.onQueryUpdated) return Promise.all(results_1).then(function() {
				return result;
			});
		}
		return Promise.resolve(result);
	};
	QueryManager.prototype.markMutationOptimistic = function(optimisticResponse, mutation) {
		var _this = this;
		var data = typeof optimisticResponse === "function" ? optimisticResponse(mutation.variables, { IGNORE }) : optimisticResponse;
		if (data === IGNORE) return false;
		this.cache.recordOptimisticTransaction(function(cache) {
			try {
				_this.markMutationResult(__assign(__assign({}, mutation), { result: { data } }), cache);
			} catch (error) {
				globalThis.__DEV__ !== false && invariant$1.error(error);
			}
		}, mutation.mutationId);
		return true;
	};
	QueryManager.prototype.fetchQuery = function(queryId, options, networkStatus) {
		return this.fetchConcastWithInfo(this.getOrCreateQuery(queryId), options, networkStatus).concast.promise;
	};
	QueryManager.prototype.getQueryStore = function() {
		var store = Object.create(null);
		this.queries.forEach(function(info, queryId) {
			store[queryId] = {
				variables: info.variables,
				networkStatus: info.networkStatus,
				networkError: info.networkError,
				graphQLErrors: info.graphQLErrors
			};
		});
		return store;
	};
	QueryManager.prototype.resetErrors = function(queryId) {
		var queryInfo = this.queries.get(queryId);
		if (queryInfo) {
			queryInfo.networkError = void 0;
			queryInfo.graphQLErrors = [];
		}
	};
	QueryManager.prototype.transform = function(document) {
		return this.documentTransform.transformDocument(document);
	};
	QueryManager.prototype.getDocumentInfo = function(document) {
		var transformCache = this.transformCache;
		if (!transformCache.has(document)) {
			var cacheEntry = {
				hasClientExports: hasClientExports(document),
				hasForcedResolvers: this.localState.shouldForceResolvers(document),
				hasNonreactiveDirective: hasDirectives(["nonreactive"], document),
				nonReactiveQuery: addNonReactiveToNamedFragments(document),
				clientQuery: this.localState.clientQuery(document),
				serverQuery: removeDirectivesFromDocument([
					{
						name: "client",
						remove: true
					},
					{ name: "connection" },
					{ name: "nonreactive" },
					{ name: "unmask" }
				], document),
				defaultVars: getDefaultValues(getOperationDefinition(document)),
				asQuery: __assign(__assign({}, document), { definitions: document.definitions.map(function(def) {
					if (def.kind === "OperationDefinition" && def.operation !== "query") return __assign(__assign({}, def), { operation: "query" });
					return def;
				}) })
			};
			transformCache.set(document, cacheEntry);
		}
		return transformCache.get(document);
	};
	QueryManager.prototype.getVariables = function(document, variables) {
		return __assign(__assign({}, this.getDocumentInfo(document).defaultVars), variables);
	};
	QueryManager.prototype.watchQuery = function(options) {
		var query = this.transform(options.query);
		options = __assign(__assign({}, options), { variables: this.getVariables(query, options.variables) });
		if (typeof options.notifyOnNetworkStatusChange === "undefined") options.notifyOnNetworkStatusChange = false;
		var queryInfo = new QueryInfo(this);
		var observable = new ObservableQuery({
			queryManager: this,
			queryInfo,
			options
		});
		observable["lastQuery"] = query;
		if (!ObservableQuery["inactiveOnCreation"].getValue()) this.queries.set(observable.queryId, queryInfo);
		queryInfo.init({
			document: query,
			observableQuery: observable,
			variables: observable.variables
		});
		return observable;
	};
	QueryManager.prototype.query = function(options, queryId) {
		var _this = this;
		if (queryId === void 0) queryId = this.generateQueryId();
		invariant$1(options.query, 38);
		invariant$1(options.query.kind === "Document", 39);
		invariant$1(!options.returnPartialData, 40);
		invariant$1(!options.pollInterval, 41);
		var query = this.transform(options.query);
		return this.fetchQuery(queryId, __assign(__assign({}, options), { query })).then(function(result) {
			return result && __assign(__assign({}, result), { data: _this.maskOperation({
				document: query,
				data: result.data,
				fetchPolicy: options.fetchPolicy,
				id: queryId
			}) });
		}).finally(function() {
			return _this.stopQuery(queryId);
		});
	};
	QueryManager.prototype.generateQueryId = function() {
		return String(this.queryIdCounter++);
	};
	QueryManager.prototype.generateRequestId = function() {
		return this.requestIdCounter++;
	};
	QueryManager.prototype.generateMutationId = function() {
		return String(this.mutationIdCounter++);
	};
	QueryManager.prototype.stopQueryInStore = function(queryId) {
		this.stopQueryInStoreNoBroadcast(queryId);
		this.broadcastQueries();
	};
	QueryManager.prototype.stopQueryInStoreNoBroadcast = function(queryId) {
		var queryInfo = this.queries.get(queryId);
		if (queryInfo) queryInfo.stop();
	};
	QueryManager.prototype.clearStore = function(options) {
		if (options === void 0) options = { discardWatches: true };
		this.cancelPendingFetches(newInvariantError(42));
		this.queries.forEach(function(queryInfo) {
			if (queryInfo.observableQuery) queryInfo.networkStatus = NetworkStatus.loading;
			else queryInfo.stop();
		});
		if (this.mutationStore) this.mutationStore = Object.create(null);
		return this.cache.reset(options);
	};
	QueryManager.prototype.getObservableQueries = function(include) {
		var _this = this;
		if (include === void 0) include = "active";
		var queries = /* @__PURE__ */ new Map();
		var queryNames = /* @__PURE__ */ new Map();
		var queryNamesAndQueryStrings = /* @__PURE__ */ new Map();
		var legacyQueryOptions = /* @__PURE__ */ new Set();
		if (Array.isArray(include)) include.forEach(function(desc) {
			if (typeof desc === "string") {
				queryNames.set(desc, desc);
				queryNamesAndQueryStrings.set(desc, false);
			} else if (isDocumentNode(desc)) {
				var queryString = print(_this.transform(desc));
				queryNames.set(queryString, getOperationName(desc));
				queryNamesAndQueryStrings.set(queryString, false);
			} else if (isNonNullObject(desc) && desc.query) legacyQueryOptions.add(desc);
		});
		this.queries.forEach(function(_a, queryId) {
			var oq = _a.observableQuery, document = _a.document;
			if (oq) {
				if (include === "all") {
					queries.set(queryId, oq);
					return;
				}
				var queryName = oq.queryName;
				if (oq.options.fetchPolicy === "standby" || include === "active" && !oq.hasObservers()) return;
				if (include === "active" || queryName && queryNamesAndQueryStrings.has(queryName) || document && queryNamesAndQueryStrings.has(print(document))) {
					queries.set(queryId, oq);
					if (queryName) queryNamesAndQueryStrings.set(queryName, true);
					if (document) queryNamesAndQueryStrings.set(print(document), true);
				}
			}
		});
		if (legacyQueryOptions.size) legacyQueryOptions.forEach(function(options) {
			var queryId = makeUniqueId("legacyOneTimeQuery");
			var queryInfo = _this.getOrCreateQuery(queryId).init({
				document: options.query,
				variables: options.variables
			});
			var oq = new ObservableQuery({
				queryManager: _this,
				queryInfo,
				options: __assign(__assign({}, options), { fetchPolicy: "network-only" })
			});
			invariant$1(oq.queryId === queryId);
			queryInfo.setObservableQuery(oq);
			queries.set(queryId, oq);
		});
		if (globalThis.__DEV__ !== false && queryNamesAndQueryStrings.size) queryNamesAndQueryStrings.forEach(function(included, nameOrQueryString) {
			if (!included) {
				var queryName = queryNames.get(nameOrQueryString);
				if (queryName) globalThis.__DEV__ !== false && invariant$1.warn(43, queryName);
				else globalThis.__DEV__ !== false && invariant$1.warn(44);
			}
		});
		return queries;
	};
	QueryManager.prototype.reFetchObservableQueries = function(includeStandby) {
		var _this = this;
		if (includeStandby === void 0) includeStandby = false;
		var observableQueryPromises = [];
		this.getObservableQueries(includeStandby ? "all" : "active").forEach(function(observableQuery, queryId) {
			var fetchPolicy = observableQuery.options.fetchPolicy;
			muteDeprecations("resetLastResults", function() {
				return observableQuery.resetLastResults();
			});
			if (includeStandby || fetchPolicy !== "standby" && fetchPolicy !== "cache-only") observableQueryPromises.push(observableQuery.refetch());
			(_this.queries.get(queryId) || observableQuery["queryInfo"]).setDiff(null);
		});
		this.broadcastQueries();
		return Promise.all(observableQueryPromises);
	};
	QueryManager.prototype.startGraphQLSubscription = function(options) {
		var _this = this;
		var query = options.query, variables = options.variables;
		var fetchPolicy = options.fetchPolicy, _a = options.errorPolicy, errorPolicy = _a === void 0 ? "none" : _a, _b = options.context, context = _b === void 0 ? {} : _b, _c = options.extensions, extensions = _c === void 0 ? {} : _c;
		query = this.transform(query);
		variables = this.getVariables(query, variables);
		var makeObservable = function(variables) {
			return _this.getObservableFromLink(query, context, variables, extensions).map(function(result) {
				if (fetchPolicy !== "no-cache") {
					if (shouldWriteResult(result, errorPolicy)) _this.cache.write({
						query,
						result: result.data,
						dataId: "ROOT_SUBSCRIPTION",
						variables
					});
					_this.broadcastQueries();
				}
				var hasErrors = graphQLResultHasError(result);
				var hasProtocolErrors = graphQLResultHasProtocolErrors(result);
				if (hasErrors || hasProtocolErrors) {
					var errors = {};
					if (hasErrors) errors.graphQLErrors = result.errors;
					if (hasProtocolErrors) errors.protocolErrors = result.extensions[PROTOCOL_ERRORS_SYMBOL];
					if (errorPolicy === "none" || hasProtocolErrors) throw new ApolloError(errors);
				}
				if (errorPolicy === "ignore") delete result.errors;
				return result;
			});
		};
		if (this.getDocumentInfo(query).hasClientExports) {
			var observablePromise_1 = this.localState.addExportedVariables(query, variables, context).then(makeObservable);
			return new Observable(function(observer) {
				var sub = null;
				observablePromise_1.then(function(observable) {
					return sub = observable.subscribe(observer);
				}, observer.error);
				return function() {
					return sub && sub.unsubscribe();
				};
			});
		}
		return makeObservable(variables);
	};
	QueryManager.prototype.stopQuery = function(queryId) {
		this.stopQueryNoBroadcast(queryId);
		this.broadcastQueries();
	};
	QueryManager.prototype.stopQueryNoBroadcast = function(queryId) {
		this.stopQueryInStoreNoBroadcast(queryId);
		this.removeQuery(queryId);
	};
	QueryManager.prototype.removeQuery = function(queryId) {
		var _a;
		this.fetchCancelFns.delete(queryId);
		if (this.queries.has(queryId)) {
			(_a = this.queries.get(queryId)) === null || _a === void 0 || _a.stop();
			this.queries.delete(queryId);
		}
	};
	QueryManager.prototype.broadcastQueries = function() {
		if (this.onBroadcast) this.onBroadcast();
		this.queries.forEach(function(info) {
			var _a;
			return (_a = info.observableQuery) === null || _a === void 0 ? void 0 : _a["notify"]();
		});
	};
	QueryManager.prototype.getLocalState = function() {
		return this.localState;
	};
	QueryManager.prototype.getObservableFromLink = function(query, context, variables, extensions, deduplication) {
		var _this = this;
		var _a;
		if (deduplication === void 0) deduplication = (_a = context === null || context === void 0 ? void 0 : context.queryDeduplication) !== null && _a !== void 0 ? _a : this.queryDeduplication;
		var observable;
		var _b = this.getDocumentInfo(query), serverQuery = _b.serverQuery, clientQuery = _b.clientQuery;
		if (serverQuery) {
			var _c = this, inFlightLinkObservables_1 = _c.inFlightLinkObservables, link = _c.link;
			var operation = {
				query: serverQuery,
				variables,
				operationName: getOperationName(serverQuery) || void 0,
				context: this.prepareContext(__assign(__assign({}, context), { forceFetch: !deduplication })),
				extensions
			};
			context = operation.context;
			if (deduplication) {
				var printedServerQuery_1 = print(serverQuery);
				var varJson_1 = canonicalStringify(variables);
				var entry = inFlightLinkObservables_1.lookup(printedServerQuery_1, varJson_1);
				observable = entry.observable;
				if (!observable) {
					var concast_1 = new Concast([execute(link, operation)]);
					observable = entry.observable = concast_1;
					concast_1.beforeNext(function cb(method, arg) {
						if (method === "next" && "hasNext" in arg && arg.hasNext) concast_1.beforeNext(cb);
						else inFlightLinkObservables_1.remove(printedServerQuery_1, varJson_1);
					});
				}
			} else observable = new Concast([execute(link, operation)]);
		} else {
			observable = new Concast([Observable.of({ data: {} })]);
			context = this.prepareContext(context);
		}
		if (clientQuery) observable = asyncMap(observable, function(result) {
			return _this.localState.runResolvers({
				document: clientQuery,
				remoteResult: result,
				context,
				variables
			});
		});
		return observable;
	};
	QueryManager.prototype.getResultsFromLink = function(queryInfo, cacheWriteBehavior, options) {
		var requestId = queryInfo.lastRequestId = this.generateRequestId();
		var linkDocument = this.cache.transformForLink(options.query);
		return asyncMap(this.getObservableFromLink(linkDocument, options.context, options.variables), function(result) {
			var graphQLErrors = getGraphQLErrorsFromResult(result);
			var hasErrors = graphQLErrors.length > 0;
			var errorPolicy = options.errorPolicy;
			if (requestId >= queryInfo.lastRequestId) {
				if (hasErrors && errorPolicy === "none") throw queryInfo.markError(new ApolloError({ graphQLErrors }));
				queryInfo.markResult(result, linkDocument, options, cacheWriteBehavior);
				queryInfo.markReady();
			}
			var aqr = {
				data: result.data,
				loading: false,
				networkStatus: NetworkStatus.ready
			};
			if (hasErrors && errorPolicy === "none") aqr.data = void 0;
			if (hasErrors && errorPolicy !== "ignore") {
				aqr.errors = graphQLErrors;
				aqr.networkStatus = NetworkStatus.error;
			}
			return aqr;
		}, function(networkError) {
			var error = isApolloError(networkError) ? networkError : new ApolloError({ networkError });
			if (requestId >= queryInfo.lastRequestId) queryInfo.markError(error);
			throw error;
		});
	};
	QueryManager.prototype.fetchConcastWithInfo = function(queryInfo, options, networkStatus, query) {
		var _this = this;
		if (networkStatus === void 0) networkStatus = NetworkStatus.loading;
		if (query === void 0) query = options.query;
		var variables = this.getVariables(query, options.variables);
		var defaults = this.defaultOptions.watchQuery;
		var _a = options.fetchPolicy, fetchPolicy = _a === void 0 ? defaults && defaults.fetchPolicy || "cache-first" : _a, _b = options.errorPolicy, errorPolicy = _b === void 0 ? defaults && defaults.errorPolicy || "none" : _b, _c = options.returnPartialData, returnPartialData = _c === void 0 ? false : _c, _d = options.notifyOnNetworkStatusChange, notifyOnNetworkStatusChange = _d === void 0 ? false : _d, _e = options.context;
		var normalized = Object.assign({}, options, {
			query,
			variables,
			fetchPolicy,
			errorPolicy,
			returnPartialData,
			notifyOnNetworkStatusChange,
			context: _e === void 0 ? {} : _e
		});
		var fromVariables = function(variables) {
			normalized.variables = variables;
			var sourcesWithInfo = _this.fetchQueryByPolicy(queryInfo, normalized, networkStatus);
			if (normalized.fetchPolicy !== "standby" && sourcesWithInfo.sources.length > 0 && queryInfo.observableQuery) queryInfo.observableQuery["applyNextFetchPolicy"]("after-fetch", options);
			return sourcesWithInfo;
		};
		var cleanupCancelFn = function() {
			return _this.fetchCancelFns.delete(queryInfo.queryId);
		};
		this.fetchCancelFns.set(queryInfo.queryId, function(reason) {
			cleanupCancelFn();
			setTimeout(function() {
				return concast.cancel(reason);
			});
		});
		var concast, containsDataFromLink;
		if (this.getDocumentInfo(normalized.query).hasClientExports) {
			concast = new Concast(this.localState.addExportedVariables(normalized.query, normalized.variables, normalized.context).then(fromVariables).then(function(sourcesWithInfo) {
				return sourcesWithInfo.sources;
			}));
			containsDataFromLink = true;
		} else {
			var sourcesWithInfo = fromVariables(normalized.variables);
			containsDataFromLink = sourcesWithInfo.fromLink;
			concast = new Concast(sourcesWithInfo.sources);
		}
		concast.promise.then(cleanupCancelFn, cleanupCancelFn);
		return {
			concast,
			fromLink: containsDataFromLink
		};
	};
	QueryManager.prototype.refetchQueries = function(_a) {
		var _this = this;
		var updateCache = _a.updateCache, include = _a.include, _b = _a.optimistic, optimistic = _b === void 0 ? false : _b, _c = _a.removeOptimistic, removeOptimistic = _c === void 0 ? optimistic ? makeUniqueId("refetchQueries") : void 0 : _c, onQueryUpdated = _a.onQueryUpdated;
		var includedQueriesById = /* @__PURE__ */ new Map();
		if (include) this.getObservableQueries(include).forEach(function(oq, queryId) {
			includedQueriesById.set(queryId, {
				oq,
				lastDiff: (_this.queries.get(queryId) || oq["queryInfo"]).getDiff()
			});
		});
		var results = /* @__PURE__ */ new Map();
		if (updateCache) this.cache.batch({
			update: updateCache,
			optimistic: optimistic && removeOptimistic || false,
			removeOptimistic,
			onWatchUpdated: function(watch, diff, lastDiff) {
				var oq = watch.watcher instanceof QueryInfo && watch.watcher.observableQuery;
				if (oq) {
					if (onQueryUpdated) {
						includedQueriesById.delete(oq.queryId);
						var result = onQueryUpdated(oq, diff, lastDiff);
						if (result === true) result = oq.refetch();
						if (result !== false) results.set(oq, result);
						return result;
					}
					if (onQueryUpdated !== null) includedQueriesById.set(oq.queryId, {
						oq,
						lastDiff,
						diff
					});
				}
			}
		});
		if (includedQueriesById.size) includedQueriesById.forEach(function(_a, queryId) {
			var oq = _a.oq, lastDiff = _a.lastDiff, diff = _a.diff;
			var result;
			if (onQueryUpdated) {
				if (!diff) diff = muteDeprecations("canonizeResults", function() {
					return _this.cache.diff(oq["queryInfo"]["getDiffOptions"]());
				});
				result = onQueryUpdated(oq, diff, lastDiff);
			}
			if (!onQueryUpdated || result === true) result = oq.refetch();
			if (result !== false) results.set(oq, result);
			if (queryId.indexOf("legacyOneTimeQuery") >= 0) _this.stopQueryNoBroadcast(queryId);
		});
		if (removeOptimistic) this.cache.removeOptimistic(removeOptimistic);
		return results;
	};
	QueryManager.prototype.maskOperation = function(options) {
		var _a, _b, _c;
		var document = options.document, data = options.data;
		if (globalThis.__DEV__ !== false) {
			var fetchPolicy = options.fetchPolicy, id = options.id;
			var operationType = (_a = getOperationDefinition(document)) === null || _a === void 0 ? void 0 : _a.operation;
			var operationId = ((_b = operationType === null || operationType === void 0 ? void 0 : operationType[0]) !== null && _b !== void 0 ? _b : "o") + id;
			if (this.dataMasking && fetchPolicy === "no-cache" && !isFullyUnmaskedOperation(document) && !this.noCacheWarningsByQueryId.has(operationId)) {
				this.noCacheWarningsByQueryId.add(operationId);
				globalThis.__DEV__ !== false && invariant$1.warn(45, (_c = getOperationName(document)) !== null && _c !== void 0 ? _c : "Unnamed ".concat(operationType !== null && operationType !== void 0 ? operationType : "operation"));
			}
		}
		return this.dataMasking ? maskOperation(data, document, this.cache) : data;
	};
	QueryManager.prototype.maskFragment = function(options) {
		var data = options.data, fragment = options.fragment, fragmentName = options.fragmentName;
		return this.dataMasking ? maskFragment(data, fragment, this.cache, fragmentName) : data;
	};
	QueryManager.prototype.fetchQueryByPolicy = function(queryInfo, _a, networkStatus) {
		var _this = this;
		var query = _a.query, variables = _a.variables, fetchPolicy = _a.fetchPolicy, refetchWritePolicy = _a.refetchWritePolicy, errorPolicy = _a.errorPolicy, returnPartialData = _a.returnPartialData, context = _a.context, notifyOnNetworkStatusChange = _a.notifyOnNetworkStatusChange;
		var oldNetworkStatus = queryInfo.networkStatus;
		queryInfo.init({
			document: query,
			variables,
			networkStatus
		});
		var readCache = function() {
			return queryInfo.getDiff();
		};
		var resultsFromCache = function(diff, networkStatus) {
			if (networkStatus === void 0) networkStatus = queryInfo.networkStatus || NetworkStatus.loading;
			var data = diff.result;
			if (globalThis.__DEV__ !== false && !returnPartialData && !equal(data, {})) logMissingFieldErrors(diff.missing);
			var fromData = function(data) {
				return Observable.of(__assign({
					data,
					loading: isNetworkRequestInFlight(networkStatus),
					networkStatus
				}, diff.complete ? null : { partial: true }));
			};
			if (data && _this.getDocumentInfo(query).hasForcedResolvers) return _this.localState.runResolvers({
				document: query,
				remoteResult: { data },
				context,
				variables,
				onlyRunForcedResolvers: true
			}).then(function(resolved) {
				return fromData(resolved.data || void 0);
			});
			if (errorPolicy === "none" && networkStatus === NetworkStatus.refetch && Array.isArray(diff.missing)) return fromData(void 0);
			return fromData(data);
		};
		var cacheWriteBehavior = fetchPolicy === "no-cache" ? 0 : networkStatus === NetworkStatus.refetch && refetchWritePolicy !== "merge" ? 1 : 2;
		var resultsFromLink = function() {
			return _this.getResultsFromLink(queryInfo, cacheWriteBehavior, {
				query,
				variables,
				context,
				fetchPolicy,
				errorPolicy
			});
		};
		var shouldNotify = notifyOnNetworkStatusChange && typeof oldNetworkStatus === "number" && oldNetworkStatus !== networkStatus && isNetworkRequestInFlight(networkStatus);
		switch (fetchPolicy) {
			default:
			case "cache-first":
				var diff = readCache();
				if (diff.complete) return {
					fromLink: false,
					sources: [resultsFromCache(diff, queryInfo.markReady())]
				};
				if (returnPartialData || shouldNotify) return {
					fromLink: true,
					sources: [resultsFromCache(diff), resultsFromLink()]
				};
				return {
					fromLink: true,
					sources: [resultsFromLink()]
				};
			case "cache-and-network":
				var diff = readCache();
				if (diff.complete || returnPartialData || shouldNotify) return {
					fromLink: true,
					sources: [resultsFromCache(diff), resultsFromLink()]
				};
				return {
					fromLink: true,
					sources: [resultsFromLink()]
				};
			case "cache-only": return {
				fromLink: false,
				sources: [resultsFromCache(readCache(), queryInfo.markReady())]
			};
			case "network-only":
				if (shouldNotify) return {
					fromLink: true,
					sources: [resultsFromCache(readCache()), resultsFromLink()]
				};
				return {
					fromLink: true,
					sources: [resultsFromLink()]
				};
			case "no-cache":
				if (shouldNotify) return {
					fromLink: true,
					sources: [resultsFromCache(queryInfo.getDiff()), resultsFromLink()]
				};
				return {
					fromLink: true,
					sources: [resultsFromLink()]
				};
			case "standby": return {
				fromLink: false,
				sources: []
			};
		}
	};
	QueryManager.prototype.getOrCreateQuery = function(queryId) {
		if (queryId && !this.queries.has(queryId)) this.queries.set(queryId, new QueryInfo(this, queryId));
		return this.queries.get(queryId);
	};
	QueryManager.prototype.prepareContext = function(context) {
		if (context === void 0) context = {};
		var newContext = this.localState.prepareContext(context);
		return __assign(__assign(__assign({}, this.defaultContext), newContext), { clientAwareness: this.clientAwareness });
	};
	return QueryManager;
}();
//#endregion
//#region node_modules/@apollo/client/core/LocalState.js
var LocalState = function() {
	function LocalState(_a) {
		var cache = _a.cache, client = _a.client, resolvers = _a.resolvers, fragmentMatcher = _a.fragmentMatcher;
		this.selectionsToResolveCache = /* @__PURE__ */ new WeakMap();
		this.cache = cache;
		if (client) this.client = client;
		if (resolvers) this.addResolvers(resolvers);
		if (fragmentMatcher) this.setFragmentMatcher(fragmentMatcher);
	}
	LocalState.prototype.addResolvers = function(resolvers) {
		var _this = this;
		this.resolvers = this.resolvers || {};
		if (Array.isArray(resolvers)) resolvers.forEach(function(resolverGroup) {
			_this.resolvers = mergeDeep(_this.resolvers, resolverGroup);
		});
		else this.resolvers = mergeDeep(this.resolvers, resolvers);
	};
	LocalState.prototype.setResolvers = function(resolvers) {
		this.resolvers = {};
		this.addResolvers(resolvers);
	};
	LocalState.prototype.getResolvers = function() {
		return this.resolvers || {};
	};
	LocalState.prototype.runResolvers = function(_a) {
		return __awaiter(this, arguments, void 0, function(_b) {
			var document = _b.document, remoteResult = _b.remoteResult, context = _b.context, variables = _b.variables, _c = _b.onlyRunForcedResolvers, onlyRunForcedResolvers = _c === void 0 ? false : _c;
			return __generator(this, function(_d) {
				if (document) return [2, this.resolveDocument(document, remoteResult.data, context, variables, this.fragmentMatcher, onlyRunForcedResolvers).then(function(localResult) {
					return __assign(__assign({}, remoteResult), { data: localResult.result });
				})];
				return [2, remoteResult];
			});
		});
	};
	LocalState.prototype.setFragmentMatcher = function(fragmentMatcher) {
		this.fragmentMatcher = fragmentMatcher;
	};
	LocalState.prototype.getFragmentMatcher = function() {
		return this.fragmentMatcher;
	};
	LocalState.prototype.clientQuery = function(document) {
		if (hasDirectives(["client"], document)) {
			if (this.resolvers) return document;
		}
		return null;
	};
	LocalState.prototype.serverQuery = function(document) {
		return removeClientSetsFromDocument(document);
	};
	LocalState.prototype.prepareContext = function(context) {
		var cache = this.cache;
		return __assign(__assign({}, context), {
			cache,
			getCacheKey: function(obj) {
				return cache.identify(obj);
			}
		});
	};
	LocalState.prototype.addExportedVariables = function(document_1) {
		return __awaiter(this, arguments, void 0, function(document, variables, context) {
			if (variables === void 0) variables = {};
			if (context === void 0) context = {};
			return __generator(this, function(_a) {
				if (document) return [2, this.resolveDocument(document, this.buildRootValueFromCache(document, variables) || {}, this.prepareContext(context), variables).then(function(data) {
					return __assign(__assign({}, variables), data.exportedVariables);
				})];
				return [2, __assign({}, variables)];
			});
		});
	};
	LocalState.prototype.shouldForceResolvers = function(document) {
		var forceResolvers = false;
		visit(document, { Directive: { enter: function(node) {
			if (node.name.value === "client" && node.arguments) {
				forceResolvers = node.arguments.some(function(arg) {
					return arg.name.value === "always" && arg.value.kind === "BooleanValue" && arg.value.value === true;
				});
				if (forceResolvers) return BREAK;
			}
		} } });
		return forceResolvers;
	};
	LocalState.prototype.buildRootValueFromCache = function(document, variables) {
		return this.cache.diff({
			query: buildQueryFromSelectionSet(document),
			variables,
			returnPartialData: true,
			optimistic: false
		}).result;
	};
	LocalState.prototype.resolveDocument = function(document_1, rootValue_1) {
		return __awaiter(this, arguments, void 0, function(document, rootValue, context, variables, fragmentMatcher, onlyRunForcedResolvers) {
			var mainDefinition, fragments, fragmentMap, selectionsToResolve, definitionOperation, defaultOperationType, _a, cache, client, execContext, isClientFieldDescendant;
			if (context === void 0) context = {};
			if (variables === void 0) variables = {};
			if (fragmentMatcher === void 0) fragmentMatcher = function() {
				return true;
			};
			if (onlyRunForcedResolvers === void 0) onlyRunForcedResolvers = false;
			return __generator(this, function(_b) {
				mainDefinition = getMainDefinition(document);
				fragments = getFragmentDefinitions(document);
				fragmentMap = createFragmentMap(fragments);
				selectionsToResolve = this.collectSelectionsToResolve(mainDefinition, fragmentMap);
				definitionOperation = mainDefinition.operation;
				defaultOperationType = definitionOperation ? definitionOperation.charAt(0).toUpperCase() + definitionOperation.slice(1) : "Query";
				_a = this, cache = _a.cache, client = _a.client;
				execContext = {
					fragmentMap,
					context: __assign(__assign({}, context), {
						cache,
						client
					}),
					variables,
					fragmentMatcher,
					defaultOperationType,
					exportedVariables: {},
					selectionsToResolve,
					onlyRunForcedResolvers
				};
				isClientFieldDescendant = false;
				return [2, this.resolveSelectionSet(mainDefinition.selectionSet, isClientFieldDescendant, rootValue, execContext).then(function(result) {
					return {
						result,
						exportedVariables: execContext.exportedVariables
					};
				})];
			});
		});
	};
	LocalState.prototype.resolveSelectionSet = function(selectionSet, isClientFieldDescendant, rootValue, execContext) {
		return __awaiter(this, void 0, void 0, function() {
			var fragmentMap, context, variables, resultsToMerge, execute;
			var _this = this;
			return __generator(this, function(_a) {
				fragmentMap = execContext.fragmentMap, context = execContext.context, variables = execContext.variables;
				resultsToMerge = [rootValue];
				execute = function(selection) {
					return __awaiter(_this, void 0, void 0, function() {
						var fragment, typeCondition;
						return __generator(this, function(_a) {
							if (!isClientFieldDescendant && !execContext.selectionsToResolve.has(selection)) return [2];
							if (!shouldInclude(selection, variables)) return [2];
							if (isField(selection)) return [2, this.resolveField(selection, isClientFieldDescendant, rootValue, execContext).then(function(fieldResult) {
								var _a;
								if (typeof fieldResult !== "undefined") resultsToMerge.push((_a = {}, _a[resultKeyNameFromField(selection)] = fieldResult, _a));
							})];
							if (isInlineFragment(selection)) fragment = selection;
							else {
								fragment = fragmentMap[selection.name.value];
								invariant$1(fragment, 21, selection.name.value);
							}
							if (fragment && fragment.typeCondition) {
								typeCondition = fragment.typeCondition.name.value;
								if (execContext.fragmentMatcher(rootValue, typeCondition, context)) return [2, this.resolveSelectionSet(fragment.selectionSet, isClientFieldDescendant, rootValue, execContext).then(function(fragmentResult) {
									resultsToMerge.push(fragmentResult);
								})];
							}
							return [2];
						});
					});
				};
				return [2, Promise.all(selectionSet.selections.map(execute)).then(function() {
					return mergeDeepArray(resultsToMerge);
				})];
			});
		});
	};
	LocalState.prototype.resolveField = function(field, isClientFieldDescendant, rootValue, execContext) {
		return __awaiter(this, void 0, void 0, function() {
			var variables, fieldName, aliasedFieldName, aliasUsed, defaultResult, resultPromise, resolverType, resolverMap, resolve;
			var _this = this;
			return __generator(this, function(_a) {
				if (!rootValue) return [2, null];
				variables = execContext.variables;
				fieldName = field.name.value;
				aliasedFieldName = resultKeyNameFromField(field);
				aliasUsed = fieldName !== aliasedFieldName;
				defaultResult = rootValue[aliasedFieldName] || rootValue[fieldName];
				resultPromise = Promise.resolve(defaultResult);
				if (!execContext.onlyRunForcedResolvers || this.shouldForceResolvers(field)) {
					resolverType = rootValue.__typename || execContext.defaultOperationType;
					resolverMap = this.resolvers && this.resolvers[resolverType];
					if (resolverMap) {
						resolve = resolverMap[aliasUsed ? fieldName : aliasedFieldName];
						if (resolve) resultPromise = Promise.resolve(cacheSlot.withValue(this.cache, resolve, [
							rootValue,
							argumentsObjectFromField(field, variables),
							execContext.context,
							{
								field,
								fragmentMap: execContext.fragmentMap
							}
						]));
					}
				}
				return [2, resultPromise.then(function(result) {
					var _a, _b;
					if (result === void 0) result = defaultResult;
					if (field.directives) field.directives.forEach(function(directive) {
						if (directive.name.value === "export" && directive.arguments) directive.arguments.forEach(function(arg) {
							if (arg.name.value === "as" && arg.value.kind === "StringValue") execContext.exportedVariables[arg.value.value] = result;
						});
					});
					if (!field.selectionSet) return result;
					if (result == null) return result;
					var isClientField = (_b = (_a = field.directives) === null || _a === void 0 ? void 0 : _a.some(function(d) {
						return d.name.value === "client";
					})) !== null && _b !== void 0 ? _b : false;
					if (Array.isArray(result)) return _this.resolveSubSelectedArray(field, isClientFieldDescendant || isClientField, result, execContext);
					if (field.selectionSet) return _this.resolveSelectionSet(field.selectionSet, isClientFieldDescendant || isClientField, result, execContext);
				})];
			});
		});
	};
	LocalState.prototype.resolveSubSelectedArray = function(field, isClientFieldDescendant, result, execContext) {
		var _this = this;
		return Promise.all(result.map(function(item) {
			if (item === null) return null;
			if (Array.isArray(item)) return _this.resolveSubSelectedArray(field, isClientFieldDescendant, item, execContext);
			if (field.selectionSet) return _this.resolveSelectionSet(field.selectionSet, isClientFieldDescendant, item, execContext);
		}));
	};
	LocalState.prototype.collectSelectionsToResolve = function(mainDefinition, fragmentMap) {
		var isSingleASTNode = function(node) {
			return !Array.isArray(node);
		};
		var selectionsToResolveCache = this.selectionsToResolveCache;
		function collectByDefinition(definitionNode) {
			if (!selectionsToResolveCache.has(definitionNode)) {
				var matches_1 = /* @__PURE__ */ new Set();
				selectionsToResolveCache.set(definitionNode, matches_1);
				visit(definitionNode, {
					Directive: function(node, _, __, ___, ancestors) {
						if (node.name.value === "client") ancestors.forEach(function(node) {
							if (isSingleASTNode(node) && isSelectionNode(node)) matches_1.add(node);
						});
					},
					FragmentSpread: function(spread, _, __, ___, ancestors) {
						var fragment = fragmentMap[spread.name.value];
						invariant$1(fragment, 22, spread.name.value);
						var fragmentSelections = collectByDefinition(fragment);
						if (fragmentSelections.size > 0) {
							ancestors.forEach(function(node) {
								if (isSingleASTNode(node) && isSelectionNode(node)) matches_1.add(node);
							});
							matches_1.add(spread);
							fragmentSelections.forEach(function(selection) {
								matches_1.add(selection);
							});
						}
					}
				});
			}
			return selectionsToResolveCache.get(definitionNode);
		}
		return collectByDefinition(mainDefinition);
	};
	return LocalState;
}();
//#endregion
//#region node_modules/@apollo/client/core/ApolloClient.js
var hasSuggestedDevtools = false;
/**
* This is the primary Apollo Client class. It is used to send GraphQL documents (i.e. queries
* and mutations) to a GraphQL spec-compliant server over an `ApolloLink` instance,
* receive results from the server and cache the results in a store. It also delivers updates
* to GraphQL queries through `Observable` instances.
*/
var ApolloClient$1 = function() {
	/**
	* Constructs an instance of `ApolloClient`.
	*
	* @example
	* ```js
	* import { ApolloClient, InMemoryCache } from '@apollo/client';
	*
	* const cache = new InMemoryCache();
	*
	* const client = new ApolloClient({
	*   // Provide required constructor fields
	*   cache: cache,
	*   uri: 'http://localhost:4000/',
	*
	*   // Provide some optional constructor fields
	*   name: 'react-web-client',
	*   version: '1.3',
	*   queryDeduplication: false,
	*   defaultOptions: {
	*     watchQuery: {
	*       fetchPolicy: 'cache-and-network',
	*     },
	*   },
	* });
	* ```
	*/
	function ApolloClient(options) {
		var _this = this;
		var _a, _b, _c;
		this.resetStoreCallbacks = [];
		this.clearStoreCallbacks = [];
		if (!options.cache) throw newInvariantError(16);
		var uri = options.uri, credentials = options.credentials, headers = options.headers, cache = options.cache, documentTransform = options.documentTransform, _d = options.ssrMode, ssrMode = _d === void 0 ? false : _d, _e = options.ssrForceFetchDelay, ssrForceFetchDelay = _e === void 0 ? 0 : _e, connectToDevTools = options.connectToDevTools, _f = options.queryDeduplication, queryDeduplication = _f === void 0 ? true : _f, defaultOptions = options.defaultOptions, defaultContext = options.defaultContext, _g = options.assumeImmutableResults, assumeImmutableResults = _g === void 0 ? cache.assumeImmutableResults : _g, resolvers = options.resolvers, typeDefs = options.typeDefs, fragmentMatcher = options.fragmentMatcher, clientAwareness = options.clientAwareness, clientAwarenessName = options.name, clientAwarenessVersion = options.version, devtools = options.devtools, dataMasking = options.dataMasking;
		if (globalThis.__DEV__ !== false) {
			warnRemovedOption(options, "connectToDevTools", "ApolloClient", "Please use `devtools.enabled` instead.");
			warnRemovedOption(options, "uri", "ApolloClient", "Please initialize an instance of `HttpLink` with `uri` instead.");
			warnRemovedOption(options, "credentials", "ApolloClient", "Please initialize an instance of `HttpLink` with `credentials` instead.");
			warnRemovedOption(options, "headers", "ApolloClient", "Please initialize an instance of `HttpLink` with `headers` instead.");
			warnRemovedOption(options, "name", "ApolloClient", "Please use the `clientAwareness.name` option instead.");
			warnRemovedOption(options, "version", "ApolloClient", "Please use the `clientAwareness.version` option instead.");
			warnRemovedOption(options, "typeDefs", "ApolloClient");
			if (!options.link) globalThis.__DEV__ !== false && invariant$1.warn(17);
		}
		var link = options.link;
		if (!link) link = uri ? new HttpLink({
			uri,
			credentials,
			headers
		}) : ApolloLink.empty();
		this.link = link;
		this.cache = cache;
		this.disableNetworkFetches = ssrMode || ssrForceFetchDelay > 0;
		this.queryDeduplication = queryDeduplication;
		this.defaultOptions = defaultOptions || Object.create(null);
		this.typeDefs = typeDefs;
		this.devtoolsConfig = __assign(__assign({}, devtools), { enabled: (_a = devtools === null || devtools === void 0 ? void 0 : devtools.enabled) !== null && _a !== void 0 ? _a : connectToDevTools });
		if (this.devtoolsConfig.enabled === void 0) this.devtoolsConfig.enabled = globalThis.__DEV__ !== false;
		if (ssrForceFetchDelay) setTimeout(function() {
			return _this.disableNetworkFetches = false;
		}, ssrForceFetchDelay);
		this.watchQuery = this.watchQuery.bind(this);
		this.query = this.query.bind(this);
		this.mutate = this.mutate.bind(this);
		this.watchFragment = this.watchFragment.bind(this);
		this.resetStore = this.resetStore.bind(this);
		this.reFetchObservableQueries = this.reFetchObservableQueries.bind(this);
		this.version = version;
		this.localState = new LocalState({
			cache,
			client: this,
			resolvers,
			fragmentMatcher
		});
		this.queryManager = new QueryManager({
			cache: this.cache,
			link: this.link,
			defaultOptions: this.defaultOptions,
			defaultContext,
			documentTransform,
			queryDeduplication,
			ssrMode,
			dataMasking: !!dataMasking,
			clientAwareness: {
				name: (_b = clientAwareness === null || clientAwareness === void 0 ? void 0 : clientAwareness.name) !== null && _b !== void 0 ? _b : clientAwarenessName,
				version: (_c = clientAwareness === null || clientAwareness === void 0 ? void 0 : clientAwareness.version) !== null && _c !== void 0 ? _c : clientAwarenessVersion
			},
			localState: this.localState,
			assumeImmutableResults,
			onBroadcast: this.devtoolsConfig.enabled ? function() {
				if (_this.devToolsHookCb) _this.devToolsHookCb({
					action: {},
					state: {
						queries: _this.queryManager.getQueryStore(),
						mutations: _this.queryManager.mutationStore || {}
					},
					dataWithOptimisticResults: _this.cache.extract(true)
				});
			} : void 0
		});
		if (this.devtoolsConfig.enabled) this.connectToDevTools();
	}
	Object.defineProperty(ApolloClient.prototype, "prioritizeCacheValues", {
		/**
		* Whether to prioritize cache values over network results when `query` or `watchQuery` is called.
		* This will essentially turn a `"network-only"` or `"cache-and-network"` fetchPolicy into a `"cache-first"` fetchPolicy,
		* but without influencing the `fetchPolicy` of the created `ObservableQuery` long-term.
		*
		* This can e.g. be used to prioritize the cache during the first render after SSR.
		*/
		get: function() {
			return this.disableNetworkFetches;
		},
		set: function(value) {
			this.disableNetworkFetches = value;
		},
		enumerable: false,
		configurable: true
	});
	ApolloClient.prototype.connectToDevTools = function() {
		if (typeof window === "undefined") return;
		var windowWithDevTools = window;
		var devtoolsSymbol = Symbol.for("apollo.devtools");
		(windowWithDevTools[devtoolsSymbol] = windowWithDevTools[devtoolsSymbol] || []).push(this);
		windowWithDevTools.__APOLLO_CLIENT__ = this;
		/**
		* Suggest installing the devtools for developers who don't have them
		*/
		if (!hasSuggestedDevtools && globalThis.__DEV__ !== false) {
			hasSuggestedDevtools = true;
			if (window.document && window.top === window.self && /^(https?|file):$/.test(window.location.protocol)) setTimeout(function() {
				if (!window.__APOLLO_DEVTOOLS_GLOBAL_HOOK__) {
					var nav = window.navigator;
					var ua = nav && nav.userAgent;
					var url = void 0;
					if (typeof ua === "string") {
						if (ua.indexOf("Chrome/") > -1) url = "https://chrome.google.com/webstore/detail/apollo-client-developer-t/jdkknkkbebbapilgoeccciglkfbmbnfm";
						else if (ua.indexOf("Firefox/") > -1) url = "https://addons.mozilla.org/en-US/firefox/addon/apollo-developer-tools/";
					}
					if (url) globalThis.__DEV__ !== false && invariant$1.log("Download the Apollo DevTools for a better development experience: %s", url);
				}
			}, 1e4);
		}
	};
	Object.defineProperty(ApolloClient.prototype, "documentTransform", {
		/**
		* The `DocumentTransform` used to modify GraphQL documents before a request
		* is made. If a custom `DocumentTransform` is not provided, this will be the
		* default document transform.
		*/
		get: function() {
			return this.queryManager.documentTransform;
		},
		enumerable: false,
		configurable: true
	});
	/**
	* Call this method to terminate any active client processes, making it safe
	* to dispose of this `ApolloClient` instance.
	*/
	ApolloClient.prototype.stop = function() {
		this.queryManager.stop();
	};
	/**
	* This watches the cache store of the query according to the options specified and
	* returns an `ObservableQuery`. We can subscribe to this `ObservableQuery` and
	* receive updated results through an observer when the cache store changes.
	*
	* Note that this method is not an implementation of GraphQL subscriptions. Rather,
	* it uses Apollo's store in order to reactively deliver updates to your query results.
	*
	* For example, suppose you call watchQuery on a GraphQL query that fetches a person's
	* first and last name and this person has a particular object identifier, provided by
	* dataIdFromObject. Later, a different query fetches that same person's
	* first and last name and the first name has now changed. Then, any observers associated
	* with the results of the first query will be updated with a new result object.
	*
	* Note that if the cache does not change, the subscriber will *not* be notified.
	*
	* See [here](https://medium.com/apollo-stack/the-concepts-of-graphql-bc68bd819be3#.3mb0cbcmc) for
	* a description of store reactivity.
	*/
	ApolloClient.prototype.watchQuery = function(options) {
		if (this.defaultOptions.watchQuery) options = mergeOptions(this.defaultOptions.watchQuery, options);
		if (this.disableNetworkFetches && (options.fetchPolicy === "network-only" || options.fetchPolicy === "cache-and-network")) options = __assign(__assign({}, options), { fetchPolicy: "cache-first" });
		if (globalThis.__DEV__ !== false) {
			warnRemovedOption(options, "canonizeResults", "client.watchQuery");
			warnRemovedOption(options, "partialRefetch", "client.watchQuery");
		}
		return this.queryManager.watchQuery(options);
	};
	/**
	* This resolves a single query according to the options specified and
	* returns a `Promise` which is either resolved with the resulting data
	* or rejected with an error.
	*
	* @param options - An object of type `QueryOptions` that allows us to
	* describe how this query should be treated e.g. whether it should hit the
	* server at all or just resolve from the cache, etc.
	*/
	ApolloClient.prototype.query = function(options) {
		if (this.defaultOptions.query) options = mergeOptions(this.defaultOptions.query, options);
		invariant$1(options.fetchPolicy !== "cache-and-network", 18);
		if (this.disableNetworkFetches && options.fetchPolicy === "network-only") options = __assign(__assign({}, options), { fetchPolicy: "cache-first" });
		if (globalThis.__DEV__ !== false) {
			warnRemovedOption(options, "canonizeResults", "client.query");
			warnRemovedOption(options, "notifyOnNetworkStatusChange", "client.query", "This option does not affect `client.query` and can be safely removed.");
			if (options.fetchPolicy === "standby") globalThis.__DEV__ !== false && invariant$1.warn(19);
		}
		return this.queryManager.query(options);
	};
	/**
	* This resolves a single mutation according to the options specified and returns a
	* Promise which is either resolved with the resulting data or rejected with an
	* error. In some cases both `data` and `errors` might be undefined, for example
	* when `errorPolicy` is set to `'ignore'`.
	*
	* It takes options as an object with the following keys and values:
	*/
	ApolloClient.prototype.mutate = function(options) {
		if (this.defaultOptions.mutate) options = mergeOptions(this.defaultOptions.mutate, options);
		return this.queryManager.mutate(options);
	};
	/**
	* This subscribes to a graphql subscription according to the options specified and returns an
	* `Observable` which either emits received data or an error.
	*/
	ApolloClient.prototype.subscribe = function(options) {
		var _this = this;
		var id = this.queryManager.generateQueryId();
		return this.queryManager.startGraphQLSubscription(options).map(function(result) {
			return __assign(__assign({}, result), { data: _this.queryManager.maskOperation({
				document: options.query,
				data: result.data,
				fetchPolicy: options.fetchPolicy,
				id
			}) });
		});
	};
	/**
	* Tries to read some data from the store in the shape of the provided
	* GraphQL query without making a network request. This method will start at
	* the root query. To start at a specific id returned by `dataIdFromObject`
	* use `readFragment`.
	*
	* @param optimistic - Set to `true` to allow `readQuery` to return
	* optimistic results. Is `false` by default.
	*/
	ApolloClient.prototype.readQuery = function(options, optimistic) {
		if (optimistic === void 0) optimistic = false;
		return this.cache.readQuery(options, optimistic);
	};
	/**
	* Watches the cache store of the fragment according to the options specified
	* and returns an `Observable`. We can subscribe to this
	* `Observable` and receive updated results through an
	* observer when the cache store changes.
	*
	* You must pass in a GraphQL document with a single fragment or a document
	* with multiple fragments that represent what you are reading. If you pass
	* in a document with multiple fragments then you must also specify a
	* `fragmentName`.
	*
	* @since 3.10.0
	* @param options - An object of type `WatchFragmentOptions` that allows
	* the cache to identify the fragment and optionally specify whether to react
	* to optimistic updates.
	*/
	ApolloClient.prototype.watchFragment = function(options) {
		var _a;
		return this.cache.watchFragment(__assign(__assign({}, options), (_a = {}, _a[Symbol.for("apollo.dataMasking")] = this.queryManager.dataMasking, _a)));
	};
	/**
	* Tries to read some data from the store in the shape of the provided
	* GraphQL fragment without making a network request. This method will read a
	* GraphQL fragment from any arbitrary id that is currently cached, unlike
	* `readQuery` which will only read from the root query.
	*
	* You must pass in a GraphQL document with a single fragment or a document
	* with multiple fragments that represent what you are reading. If you pass
	* in a document with multiple fragments then you must also specify a
	* `fragmentName`.
	*
	* @param optimistic - Set to `true` to allow `readFragment` to return
	* optimistic results. Is `false` by default.
	*/
	ApolloClient.prototype.readFragment = function(options, optimistic) {
		if (optimistic === void 0) optimistic = false;
		return this.cache.readFragment(options, optimistic);
	};
	/**
	* Writes some data in the shape of the provided GraphQL query directly to
	* the store. This method will start at the root query. To start at a
	* specific id returned by `dataIdFromObject` then use `writeFragment`.
	*/
	ApolloClient.prototype.writeQuery = function(options) {
		var ref = this.cache.writeQuery(options);
		if (options.broadcast !== false) this.queryManager.broadcastQueries();
		return ref;
	};
	/**
	* Writes some data in the shape of the provided GraphQL fragment directly to
	* the store. This method will write to a GraphQL fragment from any arbitrary
	* id that is currently cached, unlike `writeQuery` which will only write
	* from the root query.
	*
	* You must pass in a GraphQL document with a single fragment or a document
	* with multiple fragments that represent what you are writing. If you pass
	* in a document with multiple fragments then you must also specify a
	* `fragmentName`.
	*/
	ApolloClient.prototype.writeFragment = function(options) {
		var ref = this.cache.writeFragment(options);
		if (options.broadcast !== false) this.queryManager.broadcastQueries();
		return ref;
	};
	ApolloClient.prototype.__actionHookForDevTools = function(cb) {
		this.devToolsHookCb = cb;
	};
	ApolloClient.prototype.__requestRaw = function(payload) {
		return execute(this.link, payload);
	};
	/**
	* Resets your entire store by clearing out your cache and then re-executing
	* all of your active queries. This makes it so that you may guarantee that
	* there is no data left in your store from a time before you called this
	* method.
	*
	* `resetStore()` is useful when your user just logged out. You’ve removed the
	* user session, and you now want to make sure that any references to data you
	* might have fetched while the user session was active is gone.
	*
	* It is important to remember that `resetStore()` *will* refetch any active
	* queries. This means that any components that might be mounted will execute
	* their queries again using your network interface. If you do not want to
	* re-execute any queries then you should make sure to stop watching any
	* active queries.
	*/
	ApolloClient.prototype.resetStore = function() {
		var _this = this;
		return Promise.resolve().then(function() {
			return _this.queryManager.clearStore({ discardWatches: false });
		}).then(function() {
			return Promise.all(_this.resetStoreCallbacks.map(function(fn) {
				return fn();
			}));
		}).then(function() {
			return _this.reFetchObservableQueries();
		});
	};
	/**
	* Remove all data from the store. Unlike `resetStore`, `clearStore` will
	* not refetch any active queries.
	*/
	ApolloClient.prototype.clearStore = function() {
		var _this = this;
		return Promise.resolve().then(function() {
			return _this.queryManager.clearStore({ discardWatches: true });
		}).then(function() {
			return Promise.all(_this.clearStoreCallbacks.map(function(fn) {
				return fn();
			}));
		});
	};
	/**
	* Allows callbacks to be registered that are executed when the store is
	* reset. `onResetStore` returns an unsubscribe function that can be used
	* to remove registered callbacks.
	*/
	ApolloClient.prototype.onResetStore = function(cb) {
		var _this = this;
		this.resetStoreCallbacks.push(cb);
		return function() {
			_this.resetStoreCallbacks = _this.resetStoreCallbacks.filter(function(c) {
				return c !== cb;
			});
		};
	};
	/**
	* Allows callbacks to be registered that are executed when the store is
	* cleared. `onClearStore` returns an unsubscribe function that can be used
	* to remove registered callbacks.
	*/
	ApolloClient.prototype.onClearStore = function(cb) {
		var _this = this;
		this.clearStoreCallbacks.push(cb);
		return function() {
			_this.clearStoreCallbacks = _this.clearStoreCallbacks.filter(function(c) {
				return c !== cb;
			});
		};
	};
	/**
	* Refetches all of your active queries.
	*
	* `reFetchObservableQueries()` is useful if you want to bring the client back to proper state in case of a network outage
	*
	* It is important to remember that `reFetchObservableQueries()` *will* refetch any active
	* queries. This means that any components that might be mounted will execute
	* their queries again using your network interface. If you do not want to
	* re-execute any queries then you should make sure to stop watching any
	* active queries.
	* Takes optional parameter `includeStandby` which will include queries in standby-mode when refetching.
	*/
	ApolloClient.prototype.reFetchObservableQueries = function(includeStandby) {
		return this.queryManager.reFetchObservableQueries(includeStandby);
	};
	/**
	* Refetches specified active queries. Similar to "reFetchObservableQueries()" but with a specific list of queries.
	*
	* `refetchQueries()` is useful for use cases to imperatively refresh a selection of queries.
	*
	* It is important to remember that `refetchQueries()` *will* refetch specified active
	* queries. This means that any components that might be mounted will execute
	* their queries again using your network interface. If you do not want to
	* re-execute any queries then you should make sure to stop watching any
	* active queries.
	*/
	ApolloClient.prototype.refetchQueries = function(options) {
		var map = this.queryManager.refetchQueries(options);
		var queries = [];
		var results = [];
		map.forEach(function(result, obsQuery) {
			queries.push(obsQuery);
			results.push(result);
		});
		var result = Promise.all(results);
		result.queries = queries;
		result.results = results;
		result.catch(function(error) {
			globalThis.__DEV__ !== false && invariant$1.debug(20, error);
		});
		return result;
	};
	/**
	* Get all currently active `ObservableQuery` objects, in a `Map` keyed by
	* query ID strings.
	*
	* An "active" query is one that has observers and a `fetchPolicy` other than
	* "standby" or "cache-only".
	*
	* You can include all `ObservableQuery` objects (including the inactive ones)
	* by passing "all" instead of "active", or you can include just a subset of
	* active queries by passing an array of query names or DocumentNode objects.
	*/
	ApolloClient.prototype.getObservableQueries = function(include) {
		if (include === void 0) include = "active";
		return this.queryManager.getObservableQueries(include);
	};
	/**
	* Exposes the cache's complete state, in a serializable format for later restoration.
	*/
	ApolloClient.prototype.extract = function(optimistic) {
		return this.cache.extract(optimistic);
	};
	/**
	* Replaces existing state in the cache (if any) with the values expressed by
	* `serializedState`.
	*
	* Called when hydrating a cache (server side rendering, or offline storage),
	* and also (potentially) during hot reloads.
	*/
	ApolloClient.prototype.restore = function(serializedState) {
		return this.cache.restore(serializedState);
	};
	/**
	* Add additional local resolvers.
	*
	* @deprecated `addResolvers` will been removed in Apollo Client 4.0. It is
	* safe to continue using this method in Apollo Client 3.x.
	*
	* **Recommended now**
	*
	* No action needed
	*
	* **When upgrading**
	*
	* Use `client.localState.addResolvers(resolvers)`. Alternatively, store
	* the `LocalState` instance in a separate variable and call `addResolvers` on
	* that.
	*/
	ApolloClient.prototype.addResolvers = function(resolvers) {
		this.localState.addResolvers(resolvers);
	};
	/**
	* Set (override existing) local resolvers.
	*
	* @deprecated `setResolvers` will been removed in Apollo Client 4.0. It is
	* safe to continue using this method in Apollo Client 3.x.
	*
	* **Recommended now**
	*
	* If possible, stop using the `setResolvers` method.
	*
	* **When upgrading**
	*
	* Remove the use of `setResolvers`.
	*/
	ApolloClient.prototype.setResolvers = function(resolvers) {
		this.localState.setResolvers(resolvers);
	};
	/**
	* Get all registered local resolvers.
	*
	* @deprecated `getResolvers` will be removed in Apollo Client 4.0. It is
	* safe to continue using this method in Apollo Client 3.x.
	*
	* **Recommended now**
	*
	* If possible, stop using the `getResolvers` method.
	*
	* **When upgrading**
	*
	* Remove the use of `getResolvers`.
	*/
	ApolloClient.prototype.getResolvers = function() {
		return this.localState.getResolvers();
	};
	/**
	* Set a custom local state fragment matcher.
	*
	* @deprecated Custom fragment matchers will no longer be supported in Apollo
	* Client 4.0 and has been replaced by `cache.fragmentMatches`. It is safe to
	* continue using `setLocalStateFragmentMatcher` in Apollo Client 3.x.
	*
	* **Recommended now**
	*
	* No action needed
	*
	* **When upgrading**
	*
	* Leverage `possibleTypes` with `InMemoryCache` to ensure fragments match
	* correctly. Ensure `possibleTypes` include local types if needed. If working
	* with a 3rd party cache implementation, ensure the 3rd party cache implements
	* the `cache.fragmentMatches` method. This function should no longer be used.
	*/
	ApolloClient.prototype.setLocalStateFragmentMatcher = function(fragmentMatcher) {
		this.localState.setFragmentMatcher(fragmentMatcher);
	};
	/**
	* Define a new ApolloLink (or link chain) that Apollo Client will use.
	*/
	ApolloClient.prototype.setLink = function(newLink) {
		this.link = this.queryManager.link = newLink;
	};
	Object.defineProperty(ApolloClient.prototype, "defaultContext", {
		get: function() {
			return this.queryManager.defaultContext;
		},
		enumerable: false,
		configurable: true
	});
	return ApolloClient;
}();
if (globalThis.__DEV__ !== false) ApolloClient$1.prototype.getMemoryInternals = getApolloClientMemoryInternals;
//#endregion
//#region node_modules/graphql-tag/lib/index.js
var docCache = /* @__PURE__ */ new Map();
var fragmentSourceMap = /* @__PURE__ */ new Map();
var printFragmentWarnings = true;
var experimentalFragmentVariables = false;
function normalize(string) {
	return string.replace(/[\s,]+/g, " ").trim();
}
function cacheKeyFromLoc(loc) {
	return normalize(loc.source.body.substring(loc.start, loc.end));
}
function processFragments(ast) {
	var seenKeys = /* @__PURE__ */ new Set();
	var definitions = [];
	ast.definitions.forEach(function(fragmentDefinition) {
		if (fragmentDefinition.kind === "FragmentDefinition") {
			var fragmentName = fragmentDefinition.name.value;
			var sourceKey = cacheKeyFromLoc(fragmentDefinition.loc);
			var sourceKeySet = fragmentSourceMap.get(fragmentName);
			if (sourceKeySet && !sourceKeySet.has(sourceKey)) {
				if (printFragmentWarnings) console.warn("Warning: fragment with name " + fragmentName + " already exists.\ngraphql-tag enforces all fragment names across your application to be unique; read more about\nthis in the docs: http://dev.apollodata.com/core/fragments.html#unique-names");
			} else if (!sourceKeySet) fragmentSourceMap.set(fragmentName, sourceKeySet = /* @__PURE__ */ new Set());
			sourceKeySet.add(sourceKey);
			if (!seenKeys.has(sourceKey)) {
				seenKeys.add(sourceKey);
				definitions.push(fragmentDefinition);
			}
		} else definitions.push(fragmentDefinition);
	});
	return __assign(__assign({}, ast), { definitions });
}
function stripLoc(doc) {
	var workSet = new Set(doc.definitions);
	workSet.forEach(function(node) {
		if (node.loc) delete node.loc;
		Object.keys(node).forEach(function(key) {
			var value = node[key];
			if (value && typeof value === "object") workSet.add(value);
		});
	});
	var loc = doc.loc;
	if (loc) {
		delete loc.startToken;
		delete loc.endToken;
	}
	return doc;
}
function parseDocument(source) {
	var cacheKey = normalize(source);
	if (!docCache.has(cacheKey)) {
		var parsed = parse(source, {
			experimentalFragmentVariables,
			allowLegacyFragmentVariables: experimentalFragmentVariables
		});
		if (!parsed || parsed.kind !== "Document") throw new Error("Not a valid GraphQL document.");
		docCache.set(cacheKey, stripLoc(processFragments(parsed)));
	}
	return docCache.get(cacheKey);
}
function gql(literals) {
	var args = [];
	for (var _i = 1; _i < arguments.length; _i++) args[_i - 1] = arguments[_i];
	if (typeof literals === "string") literals = [literals];
	var result = literals[0];
	args.forEach(function(arg, i) {
		if (arg && arg.kind === "Document") result += arg.loc.source.body;
		else result += arg;
		result += literals[i + 1];
	});
	return parseDocument(result);
}
function resetCaches() {
	docCache.clear();
	fragmentSourceMap.clear();
}
function disableFragmentWarnings() {
	printFragmentWarnings = false;
}
function enableExperimentalFragmentVariables() {
	experimentalFragmentVariables = true;
}
function disableExperimentalFragmentVariables() {
	experimentalFragmentVariables = false;
}
var extras = {
	gql,
	resetCaches,
	disableFragmentWarnings,
	enableExperimentalFragmentVariables,
	disableExperimentalFragmentVariables
};
(function(gql_1) {
	gql_1.gql = extras.gql, gql_1.resetCaches = extras.resetCaches, gql_1.disableFragmentWarnings = extras.disableFragmentWarnings, gql_1.enableExperimentalFragmentVariables = extras.enableExperimentalFragmentVariables, gql_1.disableExperimentalFragmentVariables = extras.disableExperimentalFragmentVariables;
})(gql || (gql = {}));
gql["default"] = gql;
//#endregion
//#region node_modules/@apollo/client/core/index.js
var core_exports = /* @__PURE__ */ __exportAll({
	ApolloCache: () => ApolloCache,
	ApolloClient: () => ApolloClient$1,
	ApolloError: () => ApolloError,
	ApolloLink: () => ApolloLink,
	Cache: () => Cache,
	DocumentTransform: () => DocumentTransform,
	HttpLink: () => HttpLink,
	InMemoryCache: () => InMemoryCache$1,
	MissingFieldError: () => MissingFieldError,
	NetworkStatus: () => NetworkStatus,
	Observable: () => Observable,
	ObservableQuery: () => ObservableQuery,
	checkFetcher: () => checkFetcher,
	concat: () => concat,
	createHttpLink: () => createHttpLink$1,
	createSignalIfSupported: () => createSignalIfSupported,
	defaultDataIdFromObject: () => defaultDataIdFromObject,
	defaultPrinter: () => defaultPrinter,
	disableExperimentalFragmentVariables: () => disableExperimentalFragmentVariables,
	disableFragmentWarnings: () => disableFragmentWarnings,
	empty: () => empty,
	enableExperimentalFragmentVariables: () => enableExperimentalFragmentVariables,
	execute: () => execute,
	fallbackHttpConfig: () => fallbackHttpConfig,
	from: () => from,
	fromError: () => fromError,
	fromPromise: () => fromPromise,
	gql: () => gql,
	isApolloError: () => isApolloError,
	isNetworkRequestSettled: () => isNetworkRequestSettled,
	isReference: () => isReference,
	makeReference: () => makeReference,
	makeVar: () => makeVar,
	mergeOptions: () => mergeOptions,
	parseAndCheckHttpResponse: () => parseAndCheckHttpResponse,
	resetCaches: () => resetCaches,
	rewriteURIForGET: () => rewriteURIForGET,
	selectHttpOptionsAndBody: () => selectHttpOptionsAndBody,
	selectHttpOptionsAndBodyInternal: () => selectHttpOptionsAndBodyInternal,
	selectURI: () => selectURI,
	serializeFetchParameter: () => serializeFetchParameter,
	setLogVerbosity: () => setVerbosity,
	split: () => split,
	throwServerError: () => throwServerError,
	toPromise: () => toPromise
});
setVerbosity(globalThis.__DEV__ !== false ? "log" : "silent");
//#endregion
//#region node_modules/@apollo/client/link/context/index.js
function setContext(setter) {
	return new ApolloLink(function(operation, forward) {
		var request = __rest(operation, []);
		return new Observable(function(observer) {
			var handle;
			var closed = false;
			Promise.resolve(request).then(function(req) {
				return setter(req, operation.getContext());
			}).then(operation.setContext).then(function() {
				if (closed) return;
				handle = forward(operation).subscribe({
					next: observer.next.bind(observer),
					error: observer.error.bind(observer),
					complete: observer.complete.bind(observer)
				});
			}).catch(observer.error.bind(observer));
			return function() {
				closed = true;
				if (handle) handle.unsubscribe();
			};
		});
	});
}
//#endregion
//#region src/collab_server/graphql_client.ts
var { ApolloClient, createHttpLink, InMemoryCache } = core_exports;
var defaultGraphqlUri = "http://" + (env["HASURA_GRAPHQL_SERVER_HOSTNAME"] || "graphql_engine") + ":8080/v1/graphql";
/** Create a Hasura client that forwards the document-scoped collaboration JWT. */
function createCollabGqlClient(token, uri = defaultGraphqlUri) {
	const httpLink = createHttpLink({ uri });
	return new ApolloClient({
		link: setContext((_, { headers }) => ({ headers: {
			...headers,
			"x-hasura-admin-secret": env["HASURA_GRAPHQL_ADMIN_SECRET"],
			Authorization: "Bearer " + token
		} })).concat(httpLink),
		cache: new InMemoryCache(),
		defaultOptions: {
			query: {
				fetchPolicy: "no-cache",
				errorPolicy: "all"
			},
			watchQuery: {
				fetchPolicy: "no-cache",
				errorPolicy: "all"
			}
		}
	});
}
//#endregion
//#region src/collab_server/graphql_client.test.ts
var requestHeaders;
var server = createServer((request, response) => {
	requestHeaders = request.headers;
	response.writeHead(200, { "Content-Type": "application/json" });
	response.end(JSON.stringify({ data: { tags: { tags: [] } } }));
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
var { port } = server.address();
try {
	await createCollabGqlClient("scoped-collaboration-token", `http://127.0.0.1:${port}/v1/graphql`).query({ query: gql`
            query GetTags {
                tags(model: "report_finding_link", id: 1) {
                    tags
                }
            }
        ` });
	assert.equal(requestHeaders?.authorization, "Bearer scoped-collaboration-token");
	console.log("Collaboration GraphQL authorization header check passed.");
} finally {
	await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
}
//#endregion
export {};
