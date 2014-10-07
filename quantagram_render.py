#! /usr/bin/python

import re
import math

begin_env = re.compile(r"\\begin\s*[{]quantagram[}]", re.MULTILINE)
end_env = re.compile(r"\\end\s*[{]quantagram[}]", re.MULTILINE)
quantagram_options = re.compile(r"\\quantagramoptions\s*[{]([^}]*)[}]", re.MULTILINE)
drawing_tikz_header = r"""
\begin{tikzpicture}[thick,rotate=%(rotate)s,xscale=1,yscale=%(yscale)s]
\tikzstyle{operator} = [draw,fill=white,minimum size=1.5em] 
\tikzstyle{phase} = [draw,fill,shape=circle,minimum size=5pt,inner sep=0pt]
\tikzstyle{surround} = [fill=blue!10,thick,draw=black,rounded corners=2mm]
\matrix[row sep=%(row-sep)s, column sep=%(column-sep)s] (circuit) {
"""

def lerp(a, b, coef):
	return a[0]*(1-coef) + b[0]*coef, a[1]*(1-coef) + b[1]*coef

def error(s):
	print "="*len(s)
	print s
	print "="*len(s)
	exit(1)

def remove_latex_comments(s):
	"""remove_latex_comments(s) -> s, but after a really crummy attempt to remove comments"""
	bilge = "RaNdOmNoNcE"
	return "\n".join(i.replace("\\%", bilge).split("%", 1)[0].replace(bilge, "\\%") for i in s.split("\n"))

global_config = {
	"rotate": 0,
	"flip": 0,
	"photon-frequency": 1.0,
	"photon-amplitude": 1.0,
	"row-sep": "0.4cm",
	"column-sep": "0.8cm",
}

float_options = ["flip", "rotate", "photon-frequency", "photon-amplitude"]
string_options = ["row-sep", "column-sep"]

def global_interpret(opt):
	print "="*5, "\\quantagramoptions{%s}" % opt
	if opt == "time-up":
		global_config["rotate"] = 0
		global_config["flip"] = False
	elif opt == "time-down":
		global_config["rotate"] = 0
		global_config["flip"] = True
	elif opt == "time-left":
		global_config["rotate"] = 270
		global_config["flip"] = True
	elif opt == "time-right":
		global_config["rotate"] = 270
		global_config["flip"] = False
	elif any(opt.startswith(i+"=") for i in float_options+string_options):
		for i in float_options+string_options:
			if opt.startswith(i+"="):
				value = opt[len(i)+1:]
				if i in float_options:
					value = float(value)
				global_config[i] = value
	else:
		error("Unknown \\quantagramoptions flag: %s" % opt)

def extract_envs(s):
	s = remove_latex_comments(s)
	# Find all the options passed.
	for opts in quantagram_options.findall(s):
		opts = [i.strip() for i in opts.split(",") if i.strip()]
		map(global_interpret, opts)
	envs = []
	while True:
		match = begin_env.search(s)
		if not match: break
		s = s[match.end():]
		match = end_env.search(s)
		if not match:
			error("Unterminated quantagram environment!")
		envs.append(s[:match.start()])
		s = s[match.end():]
	return envs

class Drawing:
	def __init__(self):
		pass

	def to_code(self):
		s = drawing_tikz_header % global_config
		s += "\\end{tikzpicture}\n"
		return s

def compile_quantagram_code(code):
	d = Drawing()
	code = code.split("\n")
	for line in code:
		line = line.split("%")[0].strip()
		if not line: continue
		line = line.split(" ")
		cmd, args = line[0], line[1:]
		if cmd == "foo":
			print "Foo:", args
		else:
			error("Invalid command: %s" % cmd)
	# Do some processing on global_config.
	global_config["yscale"] = -1 if global_config["flip"] else 1
	return d.to_code()

if __name__ == "__main__":
	import sys
	if len(sys.argv) != 2:
		print "Usage: quantagram_render.py input.tex"
		exit(2)
	fd = open(sys.argv[1])
	data = fd.read()
	fd.close()
	envs = extract_envs(data)
	for i, s in enumerate(envs):
		code = compile_quantagram_code(s)
		print code
		fd = open("_quantagram_diagram%i.tex" % i, "w")
		fd.write(code)
		fd.close()

