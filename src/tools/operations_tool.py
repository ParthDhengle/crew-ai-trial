# src/agent_demo/tools/operations_tool.py
import os
from typing import List, Dict, Any, Tuple
import json
import re
# --- DYNAMIC IMPORTS FROM MODULARIZED OPERATION FILES ---
from ..utils.logger import setup_logger
from .operations.events.create_event import create_event
from .operations.events.delete_event import delete_event
from .operations.events.read_event import read_event
from .operations.events.update_event import update_event
from ..common_functions.Find_project_root import find_project_root

PROJECT_ROOT =find_project_root()
logger = setup_logger()

class OperationsTool:
	"""Dispatcher for your specified operations. Maps 'name' to funcs; validates via Firebase/json defs."""
	def __init__(self):
		self.param_definitions = self._parse_operations()
		
		# --- DYNAMIC OPERATION MAP ---
		# This map connects the string names from operations.txt to the actual imported functions.
		self.operation_map = {
			# Events (available in this repo)
			"create_event": create_event,
			"delete_event": delete_event,
			"read_event": read_event,
			"update_event": update_event,
		}

	def _parse_operations(self) -> Dict[str, Dict[str, List[str]]]:
		"""Load op defs from Firebase (fallback json)."""
		# operations could be sourced from Firebase in future; currently using local JSON
		param_defs = {}
		try:
			# Use operations.json instead of operations.txt for faster parsing
			ops_path = os.path.join(PROJECT_ROOT, "knowledge", "operations.json")
			with open(ops_path, "r", encoding="utf-8") as f:
				operations_data = json.load(f)
			
			for op in operations_data:
				name = op.get("name", "")
				required_params = op.get("required_parameters", [])
				optional_params = op.get("optional_parameters", [])
				
				param_defs[name] = {
					"required": required_params,
					"optional": optional_params
				}
			
			logger.info(f"Loaded {len(param_defs)} operation definitions from operations.json")
			return param_defs
			
		except Exception as e:
			logger.error(f"Error parsing operations.json: {e}")
			return {}
		
		return param_defs
	def _validate_params(self, operation_name: str, provided_params: dict) -> tuple[bool, str, List[str]]:
		"""Validate params against defs."""
		if operation_name not in self.param_definitions:
			return False, f"Unknown op: {operation_name}", []
		definition = self.param_definitions[operation_name]
		required_params = definition["required"]
		optional_params = definition["optional"]
		all_valid_params = required_params + optional_params
		
		# Check for invalid parameters
		invalid_params = [p for p in provided_params if p not in all_valid_params]
		if invalid_params:
			return False, f"Invalid parameters for {operation_name}: {invalid_params}. Valid: {all_valid_params}", []
		
		# Check for missing required parameters
		missing_params = [p for p in required_params if p not in provided_params]
		if missing_params:
			return False, f"Missing required parameters for {operation_name}: {missing_params}", missing_params
		
		return True, "Valid parameters", []

	def _apply_parameter_corrections(self, operation_name: str, params: dict) -> dict:
		"""Apply friendly parameter name corrections for common LLM mistakes."""
		corrected_params = params.copy()
		
		# Removed unnecessary remapping for send_email as function uses 'body' directly
		
		return corrected_params

	def _extract_parameters_from_response(self, user_response: str, missing_params: Dict[str, List[str]]) -> Dict[str, dict]:
		"""Extract parameters from user's natural language response using AI."""
		try:
			extract_prompt = f"""Extract parameter values from this user response: "{user_response}"

Missing parameters:
"""
			for op_name, params in missing_params.items():
				extract_prompt += f"- {op_name}: {', '.join(params)}\n"
			
			extract_prompt += """
Output ONLY a valid JSON object where keys are operation names and values contain the extracted parameters.
If you cannot extract a parameter value, omit it from the JSON.
Example: {"send_email": {"to": "user@example.com", "subject": "Meeting"}}"""

			# Use generate_text operation to extract parameters
			if "generate_text" in self.operation_map:
				# Not available in this trimmed map; skip extraction
				return {}
		
		except Exception as e:
			print(f"Error extracting parameters: {e}")
		
		return {}

	def ask_parameters(self, missing_params: Dict[str, List[str]], max_attempts: int = 3) -> Dict[str, dict]:
		"""Ask user for missing parameters and extract them from natural language response."""
		collected_params = {}
		remaining_params = missing_params.copy()
		
		for attempt in range(max_attempts):
			if not remaining_params:
				break
			
			# Create user-friendly question
			question = "\nI need some additional information to proceed:\n"
			for op_name, params in remaining_params.items():
				question += f"• For {op_name}: {', '.join(params)}\n"
			question += "\nPlease provide these details: "
			
			try:
				user_response = input(question)
				if not user_response.strip():
					continue
				
				# Extract parameters from response
				extracted = self._extract_parameters_from_response(user_response, remaining_params)
				
				# Update collected parameters
				for op_name, new_params in extracted.items():
					if op_name not in collected_params:
						collected_params[op_name] = {}
					collected_params[op_name].update(new_params)
				
				# Update remaining parameters
				new_remaining = {}
				for op_name, params in remaining_params.items():
					still_missing = []
					for param in params:
						if op_name not in collected_params or param not in collected_params[op_name]:
							still_missing.append(param)
					if still_missing:
						new_remaining[op_name] = still_missing
				
				remaining_params = new_remaining
				
				if not remaining_params:
					logger.info("All parameters collected successfully")
					break
					
			except KeyboardInterrupt:
				logger.warning("Parameter collection cancelled by user")
				break
			except Exception as e:
				logger.error(f"Error collecting parameters: {e}")
				continue
		
		return collected_params

	def _run(self, operations: List[Dict[str, Any]]) -> str:
		"""Exec ops sequentially; append results. Handles missing params via placeholders (no AI extract for simplicity)."""
		if not operations:
			return "No ops provided."
		lines = []
		
		try:
			# Step 1: Validate all operations and collect missing parameters
			missing_params = {}
			validated_ops = {}
			
			for op in operations:
				name = op.get("name")
				if not name:
					lines.append("❌ Operation missing 'name' field")
					continue
				
				params = op.get("parameters", {})
				
				# Check if operation exists
				if name not in self.operation_map:
					lines.append(f"❌ {name}: Operation not implemented")
					continue
				
				# Validate parameters
				is_valid, message, missing = self._validate_params(name, params)
				
				if missing:
					missing_params[name] = missing
				elif not is_valid:
					lines.append(f"❌ {name}: {message}")
					continue
				
				validated_ops[name] = params
			
			# Return early if there are fatal errors
			if lines and not missing_params:
				return "\n".join(lines)
			
			# Step 2: Collect missing parameters if any
			collected_params = {}
			if missing_params:
				print(f"\n🔍 Found {len(missing_params)} operations with missing parameters")
				collected_params = self.ask_parameters(missing_params)
			
			# Step 3: Execute all operations
			for op in operations:
				name = op.get("name")
				if name not in self.operation_map:
					continue  # Already handled above
				
				# Combine original and collected parameters
				original_params = op.get("parameters", {})
				additional_params = collected_params.get(name, {})
				final_params = {**original_params, **additional_params}
				
				# Apply corrections
				corrected_params = self._apply_parameter_corrections(name, final_params)
				
				# Final validation
				is_valid, message, missing = self._validate_params(name, corrected_params)
				if not is_valid:
					lines.append(f"❌ {name}: {message}")
					continue
				
				# Execute operation
				try:
					method = self.operation_map[name]
					success, result = method(**corrected_params)
					
					if success:
						lines.append(f"✅ {name}: {result}")
					else:
						lines.append(f"❌ {name}: {result}")
						
				except TypeError as e:
					lines.append(f"❌ {name}: Parameter error - {str(e)}")
				except Exception as e:
					lines.append(f"❌ {name}: Execution error - {str(e)}")
			
			return "\n".join(lines) if lines else "✅ All operations completed successfully"
			
		except Exception as e:
			return f"❌ Critical error in operation execution: {str(e)}"