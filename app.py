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
                    'assigned_to': None,
                    'tasks': [
                        {'id': str(uuid.uuid4()), 'name': 'Wash dishes', 'frequency': 'daily', 'assigned_to': 'Alice', 'history': []},
                        {'id': str(uuid.uuid4()), 'name': 'Clean counters', 'frequency': 'weekly', 'assigned_to': 'Bob', 'history': []}
                    ]
                },
                {
                    'id': str(uuid.uuid4()),
                    'name': 'Living Room',
                    'frequency': 'weekly',
                    'assigned_to': None,
                    'tasks': [
                        {'id': str(uuid.uuid4()), 'name': 'Vacuum floor', 'frequency': 'weekly', 'assigned_to': 'Alice', 'history': []}
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
    if not task['history']:
        return True
    last_completed = datetime.fromisoformat(task['history'][-1])
    frequency_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30)
    }
    delta = frequency_map.get(task['frequency'], timedelta(days=1))
    return datetime.now() >= last_completed + delta

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

        <!-- Filter by Person -->
        <div class="mb-6">
            <h2 class="text-xl font-semibold mb-2">Filter Tasks</h2>
            <select id="filter-person" onchange="filterTasks()" class="border p-2 rounded">
                <option value="">All Members</option>
                <!-- Populated dynamically -->
            </select>
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
            <select id="room-assigned" class="border p-2 rounded">
                <option value="">Unassigned</option>
                <!-- Populated dynamically -->
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
            renderFilterOptions();
            renderRooms();
        }

        // Render filter dropdown
        function renderFilterOptions() {
            const filterSelect = document.getElementById('filter-person');
            filterSelect.innerHTML = `<option value="">All Members</option>` + 
                data.family_members.map(member => 
                    `<option value="${member}">${member}</option>`
                ).join('');
        }

        // Render rooms and tasks
        function renderRooms(filterPerson = '') {
            const roomsDiv = document.getElementById('rooms');
            roomsDiv.innerHTML = data.rooms.map(room => {
                const tasksDue = room.tasks.filter(task => task.is_due && (!filterPerson || task.assigned_to === filterPerson));
                if (tasksDue.length === 0 && filterPerson) return '';
                return `
                    <div class="bg-white p-4 rounded shadow" draggable="true" 
                        ondragstart="dragStart(event, '${room.id}')" ondrop="drop(event, '${room.id}')" 
                        ondragover="allowDrop(event)" data-room-id="${room.id}">
                        <h2 class="text-lg font-semibold">${room.name} (${room.frequency}) 
                            ${room.assigned_to ? '- Assigned to: ' + room.assigned_to : ''}</h2>
                        <div class="mt-2">
                            <select onchange="assignRoom('${room.id}', this.value)" class="border p-1 rounded">
                                <option value="">Assign Room</option>
                                ${data.family_members.map(member => 
                                    `<option value="${member}" ${room.assigned_to === member ? 'selected' : ''}>${member}</option>`
                                ).join('')}
                            </select>
                        </div>
                        <div class="mt-2">
                            ${tasksDue.map(task => `
                                <div class="flex items-center gap-2">
                                    <input type="checkbox" ${task.history.length && !task.is_due ? 'checked' : ''} 
                                        onchange="completeTask('${room.id}', '${task.id}', this.checked)">
                                    <span>${task.name} (${task.frequency}) - Assigned to: </span>
                                    <select onchange="reassignTask('${room.id}', '${task.id}', this.value)" class="border p-1 rounded">
                                        ${data.family_members.map(member => 
                                            `<option value="${member}" ${task.assigned_to === member ? 'selected' : ''}>${member}</option>`
                                        ).join('')}
                                    </select>
                                    <button onclick="toggleHistory('${task.id}')" class="text-blue-500 hover:underline">History</button>
                                    <div id="history-${task.id}" class="hidden mt-2 ml-4">
                                        ${task.history.map((time, index) => `
                                            <div class="flex gap-2">
                                                <span>Completed: ${new Date(time).toLocaleString()}</span>
                                                <button onclick="deleteHistory('${room.id}', '${task.id}', ${index})" 
                                                    class="text-red-500 hover:underline">Delete</button>
                                            </div>
                                        `).join('')}
                                    </div>
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

        // Drag and drop functions
        let draggedRoomId = null;
        function dragStart(event, roomId) {
            draggedRoomId = roomId;
            event.dataTransfer.setData('text/plain', roomId);
        }
        function allowDrop(event) {
            event.preventDefault();
        }
        async function drop(event, targetRoomId) {
            event.preventDefault();
            if (draggedRoomId && draggedRoomId !== targetRoomId) {
                await fetch('/reorder_rooms', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({dragged_id: draggedRoomId, target_id: targetRoomId})
                });
                await loadData();
            }
        }

        // Filter tasks by person
        function filterTasks() {
            const filterPerson = document.getElementById('filter-person').value;
            renderRooms(filterPerson);
        }

        // Add room
        async function addRoom() {
            const nameInput = document.getElementById('new-room-name');
            const frequencySelect = document.getElementById('room-frequency');
            const assignedSelect = document.getElementById('room-assigned');
            const name = nameInput.value.trim();
            const frequency = frequencySelect.value;
            const assigned_to = assignedSelect.value || null;
            if (name) {
                await fetch('/add_room', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, frequency, assigned_to})
                });
                nameInput.value = '';
                assignedSelect.value = '';
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

        // Reassign task
        async function reassignTask(roomId, taskId, assignedTo) {
            await fetch('/reassign_task', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_id: roomId, task_id: taskId, assigned_to: assignedTo})
            });
            await loadData();
        }

        // Assign room
        async function assignRoom(roomId, assignedTo) {
            await fetch('/assign_room', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_id: roomId, assigned_to: assignedTo || null})
            });
            await loadData();
        }

        // Toggle task history
        function toggleHistory(taskId) {
            const historyDiv = document.getElementById(`history-${taskId}`);
            historyDiv.classList.toggle('hidden');
        }

        // Delete history entry
        async function deleteHistory(roomId, taskId, index) {
            await fetch('/delete_history', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({room_id: roomId, task_id: taskId, index})
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
    for room in data['rooms']:
        for task in room['tasks']:
            task['is_due'] = is_task_due(task)
    return jsonify(data)

@app.route('/add_room', methods=['POST'])
def add_room():
    data = load_data()
    room = {
        'id': str(uuid.uuid4()),
        'name': request.json['name'],
        'frequency': request.json['frequency'],
        'assigned_to': request.json.get('assigned_to'),
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
        'history': []
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
                    if completed:
                        task['history'].append(datetime.now().isoformat())
                    elif task['history']:
                        task['history'].pop()
                    break
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/reassign_task', methods=['POST'])
def reassign_task():
    data = load_data()
    room_id = request.json['room_id']
    task_id = request.json['task_id']
    assigned_to = request.json['assigned_to']
    for room in data['rooms']:
        if room['id'] == room_id:
            for task in room['tasks']:
                if task['id'] == task_id:
                    task['assigned_to'] = assigned_to
                    break
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/assign_room', methods=['POST'])
def assign_room():
    data = load_data()
    room_id = request.json['room_id']
    assigned_to = request.json['assigned_to']
    for room in data['rooms']:
        if room['id'] == room_id:
            room['assigned_to'] = assigned_to
            for task in room['tasks']:
                task['assigned_to'] = assigned_to if assigned_to else task['assigned_to']
            break
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/reorder_rooms', methods=['POST'])
def reorder_rooms():
    data = load_data()
    dragged_id = request.json['dragged_id']
    target_id = request.json['target_id']
    rooms = data['rooms']
    dragged_index = next(i for i, room in enumerate(rooms) if room['id'] == dragged_id)
    target_index = next(i for i, room in enumerate(rooms) if room['id'] == target_id)
    rooms.insert(target_index, rooms.pop(dragged_index))
    save_data(data)
    return jsonify({'status': 'success'})

@app.route('/delete_history', methods=['POST'])
def delete_history():
    data = load_data()
    room_id = request.json['room_id']
    task_id = request.json['task_id']
    index = request.json['index']
    for room in data['rooms']:
        if room['id'] == room_id:
            for task in room['tasks']:
                if task['id'] == task_id and index < len(task['history']):
                    task['history'].pop(index)
                    break
    save_data(data)
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    init_data()
    app.run(debug=True)