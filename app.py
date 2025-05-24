from flask import Flask, request, jsonify, render_template_string
import yaml
import os
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
DATA_FILE = 'chores.yaml'

# Initialize sample data if file doesn't exist
def init_data():
    if not os.path.exists(DATA_FILE):
        sample_data = {
            'family_members': ['Alice', 'Bob'],
            'rooms': [
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Kitchen',
                    'frequency': 'weekly',
                    'tasks': [
                        {'id': str(uuid.uuid4()), 'name': 'Wash dishes', 'frequency': 'daily', 'assigned_to': 'Alice', 'last_completed': None},
                        {'id': str(uuid.uuid4()), 'name': 'Clean counters', 'frequency': 'weekly', 'assigned_to': 'Bob', 'last_completed': None}
                    ]
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Living Room',
                    'frequency': 'weekly',
                    'tasks': [
                        {'id': str(uuid.uuid4()), 'name': 'Vacuum floor', 'frequency': 'weekly', 'assigned_to': 'Alice', 'last_completed': None}
                    ]
                }
            ]
        }
        with open(DATA_FILE, 'w') as f:
            yaml.safe_dump(sample_data, f)

# Load data from YAML
def load_data():
    if not os.path.exists(DATA_FILE):
        init_data()
    with open(DATA_FILE, 'r') as f:
        return yaml.safe_load(f) or {'family_members': [], 'rooms': []}

# Save data to YAML
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        yaml.safe_dump(data, f)

# Check if task is due
def is_task_due(task):
    if not task['last_completed']:
        return True
    last_completed = datetime.fromisoformat(task['last_completed'])
    frequency_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30)
    }
    delta = frequency_map.get(task['frequency'], timedelta(days=1))
    return datetime.now() >= last_completed + delta

@app.route('/test')
def test():
    return "Test page working!"

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Household Chores Planner</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 font-sans">
    <div class="container mx-auto p-4">
        <h1 class="text-3xl font-bold mb-4">Household Chores Planner</h1>

        <!-- Family Members Section -->
        <div class="mb-6">
            <h2 class="text-xl font-semibold mb-2">Family Members</h2>
            <div id="family-members" class="flex flex-wrap gap-2 mb-2"></div>
            <input id="new-member" type="text" placeholder="Add new family member" class="border p-2 rounded">
            <button onclick="addFamilyMember()" class="bg-blue-500 text-white p-2 rounded hover:bg-blue-600">Add Member</button>
        </div>

        <!-- Rooms Section -->
        <div id="rooms" class="space-y-4"></div>

        <!-- Add Room Form -->
        <div class="mt-6">
            <h2 class="text-xl font-semibold mb-2">Add New Room</h2>
            <input id="new-room-name" type="text" placeholder="Room name" class="border p-2 rounded">
            <select id="room-frequency" class="border p-2 rounded">
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
            </select>
            <button onclick="addRoom()" class="bg-blue-500 text-white p-2 rounded hover:bg-blue-600">Add Room</button>
        </div>
    </div>

    <script>
        let data = {};

        // Load initial data
        async function loadData() {
            const response = await fetch('/data');
            data = await response.json();
            renderFamilyMembers();
            renderRooms();
        }

        // Render family members
        function renderFamilyMembers() {
            const membersDiv = document.getElementById('family-members');
            membersDiv.innerHTML = data.family_members.map(member => 
                `<span class="bg-gray-200 px-2 py-1 rounded">${member}</span>`
            ).join('');
        }

        // Render rooms and tasks
        function renderRooms() {
            const roomsDiv = document.getElementById('rooms');
            roomsDiv.innerHTML = data.rooms.map(room => {
                const tasksDue = room.tasks.filter(task => task.is_due);
                if (tasksDue.length === 0) return '';
                return `
                    <div class="bg-white p-4 rounded shadow">
                        <h2 class="text-lg font-semibold">${room.name} (${room.frequency})</h2>
                        <div class="mt-2">
                            ${tasksDue.map(task => `
                                <div class="flex items-center gap-2">
                                    <input type="checkbox" ${task.last_completed ? '' : 'checked'} 
                                        onchange="completeTask('${room.id}', '${task.id}', this.checked)">
                                    <span>${task.name} (${task.frequency}) - Assigned to: ${task.assigned_to}</span>
                                </div>
                            `).join('')}
                        </div>
                        <div class="mt-2">
                            <input id="new-task-${room.id}" type="text" placeholder="New task" class="border p-1 rounded">
                            <select id="task-frequency-${room.id}" class="border p-1 rounded">
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="monthly">Monthly</option>
                            </select>
                            <select id="task-assigned-${room.id}" class="border p-1 rounded">
                                ${data.family_members.map(member => 
                                    `<option value="${member}">${member}</option>`
                                ).join('')}
                            </select>
                            <button onclick="addTask('${room.id}')" 
                                class="bg-green-500 text-white p-1 rounded hover:bg-green-600">Add Task</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Add family member
        async function addFamilyMember() {
            const memberInput = document.getElementById('new-member');
            const name = memberInput.value.trim();
            if (name) {
                await fetch('/add_member', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name})
                });
                memberInput.value = '';
                await loadData();
            }
        }

        // Add room
        async function addRoom() {
            const nameInput = document.getElementById('new-room-name');
            const frequencySelect = document.getElementById('room-frequency');
            const name = nameInput.value.trim();
            const frequency = frequencySelect.value;
            if (name) {
                await fetch('/add_room', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, frequency})
                });
                nameInput.value = '';
                await loadData();
            }
        }

        // Add task
        async function addTask(roomId) {
            const taskInput = document.getElementById(`new-task-${roomId}`);
            const frequencySelect = document.getElementById(`task-frequency-${roomId}`);
            const assignedSelect = document.getElementById(`task-assigned-${roomId}`);
            const name = taskInput.value.trim();
            const frequency = frequencySelect.value;
            const assigned_to = assignedSelect.value;
            if (name) {
                await fetch('/add_task', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({room_id: roomId, name, frequency, assigned_to})
                });
                taskInput.value = '';
                await loadData();
            }
        }

        // Complete task
        async function completeTask(roomId, taskId, completed) {
            await fetch('/complete_task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_id: roomId, task_id: taskId, completed})
            });
            await loadData();
        }

        // Initial load
        loadData();
    </script>
</body>
</html>
    ''')

@app.route('/data')
def get_data():
    data = load_data()
    # Add is_due flag to tasks
    for room in data['rooms']:
        for task in room['tasks']:
            task['is_due'] = is_task_due(task)
    return jsonify(data)

@app.route('/add_member', methods=['POST'])
def add_member():
    data = load_data()
    new_member = request.json['name']
    if new_member not in data['family_members']:
        data['family_members'].append(new_member)
        save_data(data)
    return jsonify({'status': 'success'})

@app.route('/add_room', methods=['POST'])
def add_room():
    data = load_data()
    room = {
        'id': str(uuid.uuid4()),
        'name': request.json['name'],
        'frequency': request.json['frequency'],
        'tasks': []
    }
    data['rooms'].append(room)
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/add_task', methods=['POST'])
def add_task():
    data = load_data()
    room_id = request.json['room_id']
    task = {
        'id': str(uuid.uuid4()),
        'name': request.json['name'],
        'frequency': request.json['frequency'],
        'assigned_to': request.json['assigned_to'],
        'last_completed': None
    }
    for room in data['rooms']:
        if room['id'] == room_id:
            room['tasks'].append(task)
            break
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/complete_task', methods=['POST'])
def complete_task():
    data = load_data()
    room_id = request.json['room_id']
    task_id = request.json['task_id']
    completed = request.json['completed']
    for room in data['rooms']:
        if room['id'] == room_id:
            for task in room['tasks']:
                if task['id'] == task_id:
                    task['last_completed'] = datetime.now().isoformat() if completed else None
                    break
    save_data(data)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_data()
    app.run(debug=True)
