#!/usr/bin/env python3
"""
Analyseur de code Python pour refactoring
Analyse un fichier Python et génère un rapport de complexité
"""

import ast
import os
import sys
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import argparse

class CodeAnalyzer(ast.NodeVisitor):
	def __init__(self):
		self.functions = []
		self.classes = []
		self.imports = []
		self.globals = []
		self.complexity_map = defaultdict(int)
		self.line_count = 0
		self.duplicated_lines = []
		
	def visit_FunctionDef(self, node):
		"""Analyse des fonctions"""
		func_info = {
			'name': node.name,
			'line_start': node.lineno,
			'line_end': node.end_lineno or node.lineno,
			'lines': (node.end_lineno or node.lineno) - node.lineno + 1,
			'args_count': len(node.args.args),
			'complexity': self._calculate_complexity(node),
			'docstring': ast.get_docstring(node) is not None,
			'decorators': len(node.decorator_list)
		}
		self.functions.append(func_info)
		self.generic_visit(node)
		
	def visit_ClassDef(self, node):
		"""Analyse des classes"""
		methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
		class_info = {
			'name': node.name,
			'line_start': node.lineno,
			'line_end': node.end_lineno or node.lineno,
			'lines': (node.end_lineno or node.lineno) - node.lineno + 1,
			'methods_count': len(methods),
			'docstring': ast.get_docstring(node) is not None,
			'inheritance': len(node.bases)
		}
		self.classes.append(class_info)
		self.generic_visit(node)
		
	def visit_Import(self, node):
		"""Analyse des imports"""
		for alias in node.names:
			self.imports.append({
				'type': 'import',
				'name': alias.name,
				'alias': alias.asname,
				'line': node.lineno
			})
		self.generic_visit(node)
		
	def visit_ImportFrom(self, node):
		"""Analyse des imports from"""
		for alias in node.names:
			self.imports.append({
				'type': 'from',
				'module': node.module,
				'name': alias.name,
				'alias': alias.asname,
				'line': node.lineno
			})
		self.generic_visit(node)
		
	def visit_Global(self, node):
		"""Variables globales"""
		self.globals.extend(node.names)
		self.generic_visit(node)
		
	def _calculate_complexity(self, node):
		"""Calcul complexité cyclomatique (approximative)"""
		complexity = 1  # Base complexity
		
		for child in ast.walk(node):
			if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
				complexity += 1
			elif isinstance(child, ast.ExceptHandler):
				complexity += 1
			elif isinstance(child, ast.comprehension):
				complexity += 1
			elif isinstance(child, ast.BoolOp):
				complexity += len(child.values) - 1
				
		return complexity

def analyze_file(filepath: str) -> Dict[str, Any]:
	"""Analyse complète d'un fichier Python"""
	
	if not os.path.exists(filepath):
		raise FileNotFoundError(f"File {filepath} not found")
		
	with open(filepath, 'r', encoding='utf-8') as f:
		content = f.read()
		lines = content.splitlines()
		
	try:
		tree = ast.parse(content)
	except SyntaxError as e:
		raise SyntaxError(f"Syntax error in {filepath}: {e}")
		
	analyzer = CodeAnalyzer()
	analyzer.line_count = len(lines)
	analyzer.visit(tree)
	
	# Analyse supplémentaire
	analysis = {
		'file_info': {
			'filepath': filepath,
			'total_lines': len(lines),
			'non_empty_lines': len([l for l in lines if l.strip()]),
			'comment_lines': len([l for l in lines if l.strip().startswith('#')]),
		},
		'functions': analyzer.functions,
		'classes': analyzer.classes,
		'imports': analyzer.imports,
		'globals': analyzer.globals,
		'hotspots': [],
		'recommendations': []
	}
	
	# Identification des hotspots
	analysis['hotspots'] = identify_hotspots(analysis)
	analysis['recommendations'] = generate_recommendations(analysis)
	
	return analysis

def identify_hotspots(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
	"""Identifie les zones problématiques"""
	hotspots = []
	
	# Fonctions trop longues
	for func in analysis['functions']:
		if func['lines'] > 50:
			hotspots.append({
				'type': 'long_function',
				'severity': 'high' if func['lines'] > 100 else 'medium',
				'item': func['name'],
				'details': f"{func['lines']} lines (start: line {func['line_start']})",
				'recommendation': 'Split into smaller functions'
			})
			
		# Complexité élevée
		if func['complexity'] > 10:
			hotspots.append({
				'type': 'high_complexity',
				'severity': 'high' if func['complexity'] > 20 else 'medium',
				'item': func['name'],
				'details': f"Complexity: {func['complexity']}",
				'recommendation': 'Simplify logic, extract conditions'
			})
			
		# Trop de paramètres
		if func['args_count'] > 5:
			hotspots.append({
				'type': 'too_many_args',
				'severity': 'medium',
				'item': func['name'],
				'details': f"{func['args_count']} parameters",
				'recommendation': 'Use dataclass or config object'
			})
	
	# Classes trop grosses
	for cls in analysis['classes']:
		if cls['lines'] > 200:
			hotspots.append({
				'type': 'large_class',
				'severity': 'high' if cls['lines'] > 400 else 'medium',
				'item': cls['name'],
				'details': f"{cls['lines']} lines, {cls['methods_count']} methods",
				'recommendation': 'Split responsibilities, extract classes'
			})
	
	return sorted(hotspots, key=lambda x: {'high': 3, 'medium': 2, 'low': 1}[x['severity']], reverse=True)

def generate_recommendations(analysis: Dict[str, Any]) -> List[str]:
	"""Génère des recommandations de refactoring"""
	recommendations = []
	
	total_lines = analysis['file_info']['total_lines']
	func_count = len(analysis['functions'])
	class_count = len(analysis['classes'])
	
	if total_lines > 1000:
		recommendations.append(f"🚨 File too large ({total_lines} lines). Split into modules by domain.")
		
	if func_count > 50:
		recommendations.append(f"📦 Too many functions ({func_count}). Group related functions into classes.")
		
	# Analyse des imports
	import_count = len(analysis['imports'])
	if import_count > 20:
		recommendations.append(f"📚 Many imports ({import_count}). Consider dependency injection or facade pattern.")
		
	# Fonctions sans docstring
	undocumented_funcs = [f for f in analysis['functions'] if not f['docstring']]
	if len(undocumented_funcs) > 5:
		recommendations.append(f"📝 {len(undocumented_funcs)} functions without docstrings. Add documentation.")
		
	# Complexité globale
	avg_complexity = sum(f['complexity'] for f in analysis['functions']) / max(func_count, 1)
	if avg_complexity > 5:
		recommendations.append(f"🧠 High average complexity ({avg_complexity:.1f}). Simplify business logic.")
		
	return recommendations

def print_report(analysis: Dict[str, Any]):
	"""Affiche le rapport d'analyse"""
	
	print("=" * 80)
	print(f"📊 CODE ANALYSIS REPORT: {analysis['file_info']['filepath']}")
	print("=" * 80)
	
	# Infos générales
	info = analysis['file_info']
	print(f"\n📋 FILE OVERVIEW:")
	print(f"  • Total lines: {info['total_lines']}")
	print(f"  • Code lines: {info['non_empty_lines']}")  
	print(f"  • Comment lines: {info['comment_lines']}")
	print(f"  • Functions: {len(analysis['functions'])}")
	print(f"  • Classes: {len(analysis['classes'])}")
	print(f"  • Imports: {len(analysis['imports'])}")
	
	# Top fonctions problématiques
	print(f"\n🔥 TOP PROBLEMATIC FUNCTIONS:")
	problem_funcs = sorted(analysis['functions'], 
						  key=lambda x: (x['lines'] + x['complexity'] * 2), 
						  reverse=True)[:5]
	
	for func in problem_funcs:
		print(f"  • {func['name']:<20} | {func['lines']:3d} lines | complexity: {func['complexity']:2d} | args: {func['args_count']}")
	
	# Hotspots
	if analysis['hotspots']:
		print(f"\n⚠️  HOTSPOTS TO REFACTOR:")
		for hotspot in analysis['hotspots'][:10]:  # Top 10
			severity_icon = "🚨" if hotspot['severity'] == 'high' else "⚠️"
			print(f"  {severity_icon} {hotspot['item']:<25} | {hotspot['details']}")
			print(f"     💡 {hotspot['recommendation']}")
	
	# Recommandations
	if analysis['recommendations']:
		print(f"\n💡 REFACTORING RECOMMENDATIONS:")
		for i, rec in enumerate(analysis['recommendations'], 1):
			print(f"  {i}. {rec}")
	
	# Stratégie de refactoring
	print(f"\n🎯 REFACTORING STRATEGY:")
	print(f"  1. Extract utility functions from large functions")
	print(f"  2. Split classes with >200 lines into smaller ones")
	print(f"  3. Create separate modules for different domains")
	print(f"  4. Add tests for critical functions before refactoring")
	print(f"  5. Use dependency injection to reduce coupling")

def main():
	parser = argparse.ArgumentParser(description='Analyze Python code for refactoring')
	parser.add_argument('file', help='Python file to analyze')
	parser.add_argument('--json', action='store_true', help='Output as JSON')
	
	args = parser.parse_args()
	
	try:
		analysis = analyze_file(args.file)
		
		if args.json:
			import json
			print(json.dumps(analysis, indent=2))
		else:
			print_report(analysis)
			
	except Exception as e:
		print(f"Error analyzing file: {e}", file=sys.stderr)
		sys.exit(1)

if __name__ == "__main__":
	main()