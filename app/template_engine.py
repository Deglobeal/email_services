# app/template_engine.py
import jinja2
from typing import Dict, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TemplateEngine:
    def __init__(self):
        self.env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def validate_variables(self, template: str, provided_vars: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that all required template variables are provided"""
        try:
            parsed_template = self.env.parse(template)
            required_vars = jinja2.meta.find_undeclared_variables(parsed_template) # type: ignore
            
            missing_vars = required_vars - set(provided_vars.keys())
            if missing_vars:
                raise ValueError(f"Missing required variables: {missing_vars}")
            
            # Return only the variables that are actually used in the template
            used_vars = {k: v for k, v in provided_vars.items() if k in required_vars}
            return used_vars
            
        except jinja2.exceptions.TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise ValueError(f"Invalid template syntax: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def render_template(self, template_content: str, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        try:
            template = self.env.from_string(template_content)
            rendered = template.render(**variables)
            return rendered
        except jinja2.exceptions.UndefinedError as e:
            logger.error(f"Undefined variable in template: {e}")
            raise ValueError(f"Missing variable in template: {e}")
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            raise
    
    def render_email(self, subject_template: str, body_template: str, variables: Dict[str, Any]) -> tuple[str, str]:
        """Render both subject and body templates"""
        try:
            validated_vars = self.validate_variables(body_template, variables)
            
            # Render subject (might have different variables)
            subject_vars = self.validate_variables(subject_template, variables)
            rendered_subject = self.render_template(subject_template, subject_vars)
            
            # Render body
            rendered_body = self.render_template(body_template, validated_vars)
            
            return rendered_subject, rendered_body
            
        except Exception as e:
            logger.error(f"Email rendering failed: {e}")
            raise

template_engine = TemplateEngine()