
import copy
import os
import logging

from jinja2.exceptions import TemplateRuntimeError, TemplateSyntaxError, UndefinedError
from pptx import Presentation
from docxtpl import DocxTemplate

from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.reportwriter import prepare_jinja2_env

logger = logging.getLogger(__name__)


class TemplateLinter:
    """Lint template files to catch undefined variables and syntax errors."""

    def __init__(self, template):
        self.template = template
        self.template_loc = template.document.path
        self.jinja_template_env = prepare_jinja2_env(debug=True)

    def lint_docx(self):
        """
        Lint the provided Word docx file from :model:`reporting.ReportTemplate`.
        """
        results = {"result": "success", "warnings": [], "errors": []}
        if self.template_loc:
            if os.path.exists(self.template_loc):
                logger.info("Found template file at %s", self.template_loc)
                try:
                    # Step 1: Load the document as a template
                    template_document = DocxTemplate(self.template_loc)
                    logger.info("Template loaded for linting")

                    undefined_vars = template_document.get_undeclared_template_variables(self.jinja_template_env)
                    if undefined_vars:
                        for variable in undefined_vars:
                            if variable not in LINTER_CONTEXT:
                                results["warnings"].append(f"Potential undefined variable: {variable}")

                    # Step 2: Check document's styles
                    document_styles = template_document.styles
                    if "Bullet List" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Bullet List"
                        )
                    if "Number List" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Number List"
                        )
                    if "CodeBlock" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): CodeBlock"
                        )
                    if "CodeInline" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): CodeInline"
                        )
                    if "Caption" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Caption"
                        )
                    if "List Paragraph" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): List Paragraph"
                        )
                    if "Blockquote" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Blockquote"
                        )
                    if "Blockquote" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Blockquote"
                        )
                    if "Table Grid" not in document_styles:
                        results["errors"].append("Template is missing a required style (see documentation): Table Grid")
                    if self.template.p_style:
                        if self.template.p_style not in document_styles:
                            results["warnings"].append(
                                f"Template is missing your configured default paragraph style: {self.template.p_style}"
                            )

                    if results["warnings"]:
                        results["result"] = "warning"

                    logger.info("Completed Word style checks")

                    # Step 3: Prepare context
                    context = copy.deepcopy(LINTER_CONTEXT)
                    for field in ExtraFieldSpec.objects.filter(target_model=Report._meta.label):
                        context["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=Project._meta.label):
                        context["project"]["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=Client._meta.label):
                        context["client"]["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=Finding._meta.label):
                        for finding in context["findings"]:
                            finding["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=OplogEntry._meta.label):
                        for log in context["logs"]:
                            for entry in log["entries"]:
                                entry["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=Domain._meta.label):
                        for domain in context["infrastructure"]["domains"]:
                            domain["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=StaticServer._meta.label):
                        for server in context["infrastructure"]["servers"]:
                            server["extra_fields"][field.internal_name] = field.default_value()
                    for field in ExtraFieldSpec.objects.filter(target_model=Observation._meta.label):
                        for obs in context["observations"]:
                            obs["extra_fields"][field.internal_name] = field.default_value()

                    # Step 4: Test rendering the document
                    try:
                        template_document.render(context, self.jinja_template_env, autoescape=True)
                        undefined_vars = template_document.undeclared_template_variables
                        if undefined_vars:
                            for variable in undefined_vars:
                                results["warnings"].append(f"Undefined variable: {variable}")
                        if results["warnings"]:
                            results["result"] = "warning"
                        logger.info("Completed document rendering test")
                    except TemplateSyntaxError as error:
                        logger.exception("Template syntax error: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [f"Jinja2 template syntax error: {error.message}"],
                        }
                        if error.message == "expected token 'end of print statement', got 'such'":
                            results["errors"].append(
                                "The above error means you may have a typo in a variable name or expression"
                            )
                    except UndefinedError as error:
                        logger.error("Template syntax error: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [f"Jinja2 template syntax error: {error.message}"],
                        }
                    except InvalidFilterValue as error:
                        logger.error("Invalid value provided to filter: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [f"Invalid filter value: {error.message}"],
                        }
                    except TypeError as error:
                        logger.error("Invalid value provided to filter or expression: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [f"Invalid value provided to filter or expression: {error}"],
                        }
                    except TemplateRuntimeError as error:
                        logger.error("Invalid filter or expression: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [f"Invalid filter or expression: {error}"],
                        }
                except Exception:
                    logger.exception("Template failed rendering")
                    results = {
                        "result": "failed",
                        "errors": ["Template rendering failed unexpectedly"],
                    }
            else:
                logger.error("Template file path did not exist: %s", self.template_loc)
                results = {
                    "result": "failed",
                    "errors": ["Template file does not exist – upload it again"],
                }
        else:
            logger.error("Received a `None` value for template location")

        logger.info("Template linting completed")
        return results

    def lint_pptx(self):
        """
        Lint the provided PowerPoint pptx file from :model:`reporting.ReportTemplate`.
        """
        results = {"result": "success", "warnings": [], "errors": []}
        if self.template_loc:
            if os.path.exists(self.template_loc):
                logger.info("Found template file at %s", self.template_loc)
                try:
                    # Test 1: Check if the document is a PPTX file
                    template_document = Presentation(self.template_loc)

                    # Test 2: Check for existing slides
                    slide_count = len(template_document.slides)
                    logger.info("Slide count was %s", slide_count)
                    if slide_count > 0:
                        results["warnings"].append(
                            "Template can be used, but it has slides when it should be empty (see documentation)"
                        )
                except ValueError:
                    logger.exception(
                        "Failed to load the provided template document because it is not a PowerPoint file: %s",
                        self.template_loc,
                    )
                    results = {
                        "result": "failed",
                        "errors": ["Template file is not a PowerPoint presentation"],
                    }
                except TypeError as error:
                    logger.error("Invalid value provided to filter or expression: %s", error)
                    results = {
                        "result": "failed",
                        "errors": [f"Invalid value provided to filter or expression: {error}"],
                    }
                except TemplateRuntimeError as error:
                    logger.error("Invalid filter or expression: %s", error)
                    results = {
                        "result": "failed",
                        "errors": [f"Invalid filter or expression: {error}"],
                    }
                except Exception:
                    logger.exception("Template failed rendering")
                    results = {
                        "result": "failed",
                        "errors": ["Template rendering failed unexpectedly"],
                    }
            else:
                logger.error("Template file path did not exist: %s", self.template_loc)
                results = {
                    "result": "failed",
                    "errors": ["Template file does not exist – upload it again"],
                }
        else:
            logger.error("Received a `None` value for template location")

        logger.info("Template linting completed")
        return results
