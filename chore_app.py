import os
import uuid
from datetime import datetime, timedelta

import yaml
from flask import Flask, jsonify, redirect, render_template_string, request, url_for

app = Flask(__name__)
DATA_FILE = "chores_data.yaml"

# --- Helper Functions ---
def load_data():
    """Loads data from the YAML file."""
    if not os.path.exists(DATA_FILE):
        return {
            "rooms": {
                "kitchen": {
                    "name": "Kitchen",
                    "tasks": {
                        "task1": {
                            "name": "Wipe counters",
                            "done": False,
                            "frequency_days": 1,
                            "assigned_to": None,
                            "last_done": None,
                        },
                        "task2": {
                            "name": "Do dishes",
                            "done": False,
                            "frequency_days": 1,
                            "assigned_to": None,
                            "last_done": None,
                        },
                    },
                    "default_frequency_days": 7,
                },
                "living_room": {
                    "name": "Living Room",
                    "tasks": {
                        "task3": {
                            "name": "Vacuum floor",
                            "done": False,
                            "frequency_days": 7,
                            "assigned_to": None,
                            "last_done": None,
                        }
                    },
                    "default_frequency_days": 7,
                },
            },
            "members": {"member1": {"name": "Alice"}, "member2": {"name": "Bob"}},
            "next_ids": {"room": 3, "task": 4, "member": 3}, # Keep track of next IDs
        }
    with open(DATA_FILE, "r") as f:
        return yaml.safe_load(f)

def save_data(data):
    """Saves data to the YAML file."""
    with open(DATA_FILE, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

def is_task_due(task):
    """Checks if a task is due based on its frequency and last_done date."""
    if task.get("done") and task.get("last_done") and task.get("frequency_days"):
        last_done_date = datetime.strptime(task["last_done"], "%Y-%m-%d")
        if last_done_date + timedelta(days=int(task["frequency_days"])) <= datetime.now():
            return True # Due, needs to be undone for the new cycle
        return False # Still within the frequency, no need to show if "Show only due"
    elif not task.get("done") and task.get("frequency_days"): # Not done yet, but has a frequency
        return True
    elif not task.get("frequency_days"): # No frequency, always show if not done
        return not task.get("done")
    return False # Default to false if conditions aren't met


# --- Routes ---
@app.route("/")
def index():
    """Main page displaying rooms, tasks, and members."""
    data = load_data()
    show_only_due = request.args.get("show_due", "false").lower() == "true"
    current_member_filter = request.args.get("member_filter", "all")

    # Reset tasks that are due
    for room_id, room in data["rooms"].items():
        for task_id, task in room["tasks"].items():
            if task.get("done") and task.get("last_done") and task.get("frequency_days"):
                last_done_date = datetime.strptime(task["last_done"], "%Y-%m-%d")
                if last_done_date + timedelta(days=int(task["frequency_days"])) <= datetime.now():
                    task["done"] = False # Reset for the new cycle
                    # task["last_done"] = None # Optionally clear last_done or keep for history

    # Apply filters
    filtered_rooms = {}
    for room_id, room_details in data["rooms"].items():
        visible_tasks = {}
        for task_id, task_details in room_details["tasks"].items():
            task_is_due_for_display = is_task_due(task_details)
            assigned_to_current_filter = (
                current_member_filter == "all"
                or task_details.get("assigned_to") == current_member_filter
                or (current_member_filter == "unassigned" and not task_details.get("assigned_to"))
            )

            if show_only_due:
                if task_is_due_for_display and not task_details["done"] and assigned_to_current_filter:
                    visible_tasks[task_id] = task_details
            elif assigned_to_current_filter:
                 visible_tasks[task_id] = task_details


        if visible_tasks or not show_only_due : # If not filtering by due, show room if it has any tasks or allow adding tasks
            filtered_rooms[room_id] = {**room_details, "tasks": visible_tasks}
        elif not show_only_due and not visible_tasks and not room_details["tasks"]: # Show empty rooms if not filtering
             filtered_rooms[room_id] = room_details


    save_data(data) # Save potential changes from resetting due tasks

    return render_template_string(
        HTML_TEMPLATE,
        rooms=filtered_rooms,
        all_rooms=data["rooms"], # for dropdowns
        members=data["members"],
        show_only_due=show_only_due,
        current_member_filter=current_member_filter
    )


@app.route("/add_room", methods=["POST"])
def add_room():
    """Adds a new room."""
    data = load_data()
    room_name = request.form.get("room_name")
    default_frequency = request.form.get("room_default_frequency", 7)
    if room_name:
        room_id = f"room{data['next_ids']['room']}"
        data["next_ids"]["room"] += 1
        data["rooms"][room_id] = {
            "name": room_name,
            "tasks": {},
            "default_frequency_days": int(default_frequency),
        }
        save_data(data)
    return redirect(url_for("index"))


@app.route("/add_task/<room_id>", methods=["POST"])
def add_task(room_id):
    """Adds a new task to a specific room."""
    data = load_data()
    if room_id in data["rooms"]:
        task_name = request.form.get("task_name")
        task_frequency = request.form.get(
            "task_frequency", data["rooms"][room_id]["default_frequency_days"]
        )
        if task_name:
            task_id = f"task{data['next_ids']['task']}"
            data["next_ids"]["task"] += 1
            data["rooms"][room_id]["tasks"][task_id] = {
                "name": task_name,
                "done": False,
                "frequency_days": int(task_frequency) if task_frequency else None,
                "assigned_to": None,
                "last_done": None,
            }
            save_data(data)
    return redirect(url_for("index"))


@app.route("/toggle_task/<room_id>/<task_id>", methods=["POST"])
def toggle_task(room_id, task_id):
    """Toggles the 'done' status of a task."""
    data = load_data()
    if (
        room_id in data["rooms"]
        and task_id in data["rooms"][room_id]["tasks"]
    ):
        task = data["rooms"][room_id]["tasks"][task_id]
        task["done"] = not task["done"]
        if task["done"]:
            task["last_done"] = datetime.now().strftime("%Y-%m-%d")
        else:
            task["last_done"] = None # Clear last_done if unchecking
        save_data(data)
        # For AJAX response if you implement it later
        # return jsonify({"success": True, "done": task["done"], "last_done": task["last_done"]})
    return redirect(request.referrer or url_for("index"))


@app.route("/update_task_frequency/<room_id>/<task_id>", methods=["POST"])
def update_task_frequency(room_id, task_id):
    """Updates the frequency of a task."""
    data = load_data()
    if (
        room_id in data["rooms"]
        and task_id in data["rooms"][room_id]["tasks"]
    ):
        try:
            new_frequency = request.form.get("task_frequency")
            if new_frequency is None or new_frequency.strip() == "": # Allows clearing frequency
                data["rooms"][room_id]["tasks"][task_id]["frequency_days"] = None
            else:
                data["rooms"][room_id]["tasks"][task_id]["frequency_days"] = int(new_frequency)
            save_data(data)
        except ValueError:
            # Handle cases where conversion to int might fail, though input type=number helps
            pass # Or return an error message
    return redirect(request.referrer or url_for("index"))


@app.route("/update_room_frequency/<room_id>", methods=["POST"])
def update_room_frequency(room_id):
    """Updates the default frequency for tasks in a room."""
    data = load_data()
    if room_id in data["rooms"]:
        try:
            new_frequency = request.form.get("room_frequency")
            if new_frequency is None or new_frequency.strip() == "":
                data["rooms"][room_id]["default_frequency_days"] = None
            else:
                data["rooms"][room_id]["default_frequency_days"] = int(new_frequency)
            save_data(data)
        except ValueError:
            pass
    return redirect(request.referrer or url_for("index"))


@app.route("/add_member", methods=["POST"])
def add_member():
    """Adds a new family member."""
    data = load_data()
    member_name = request.form.get("member_name")
    if member_name:
        member_id = f"member{data['next_ids']['member']}"
        data["next_ids"]["member"] += 1
        data["members"][member_id] = {"name": member_name}
        save_data(data)
    return redirect(url_for("index"))


@app.route("/assign_task/<room_id>/<task_id>", methods=["POST"])
def assign_task(room_id, task_id):
    """Assigns a task to a family member."""
    data = load_data()
    if (
        room_id in data["rooms"]
        and task_id in data["rooms"][room_id]["tasks"]
    ):
        member_id = request.form.get("member_id")
        # If "unassign" is selected, member_id will be an empty string or a specific value
        if member_id == "unassign" or not member_id :
            data["rooms"][room_id]["tasks"][task_id]["assigned_to"] = None
        elif member_id in data["members"]:
            data["rooms"][room_id]["tasks"][task_id]["assigned_to"] = member_id
        save_data(data)
    return redirect(request.referrer or url_for("index"))

@app.route("/delete_task/<room_id>/<task_id>", methods=["POST"])
def delete_task(room_id, task_id):
    data = load_data()
    if room_id in data["rooms"] and task_id in data["rooms"][room_id]["tasks"]:
        del data["rooms"][room_id]["tasks"][task_id]
        save_data(data)
    return redirect(request.referrer or url_for("index"))

@app.route("/delete_room/<room_id>", methods=["POST"])
def delete_room(room_id):
    data = load_data()
    if room_id in data["rooms"]:
        del data["rooms"][room_id]
        save_data(data)
    return redirect(url_for("index"))

@app.route("/delete_member/<member_id>", methods=["POST"])
def delete_member(member_id):
    data = load_data()
    if member_id in data["members"]:
        # Unassign tasks from this member
        for r_id, room in data["rooms"].items():
            for t_id, task in room["tasks"].items():
                if task.get("assigned_to") == member_id:
                    task["assigned_to"] = None
        del data["members"][member_id]
        save_data(data)
    return redirect(url_for("index"))


# --- HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Household Chore Planner</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #333; }
        h1 { text-align: center; margin-bottom: 20px; }
        .room { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 5px; background-color: #f9f9f9; }
        .room h2 { margin-top: 0; border-bottom: 1px solid #eee; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center;}
        .task { display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
        .task:last-child { border-bottom: none; }
        .task input[type="checkbox"] { margin-right: 10px; transform: scale(1.2); }
        .task label { flex-grow: 1; }
        .task .actions { margin-left: auto; display: flex; align-items: center; gap: 10px;}
        .task .frequency, .task .assignment { font-size: 0.9em; color: #555; margin-left:15px;}
        .task .last-done { font-size: 0.8em; color: #777; margin-left: 5px; }
        .task.done label { text-decoration: line-through; color: #888; }
        .form-section { margin-bottom: 30px; padding: 15px; background-color: #e9e9e9; border-radius: 5px; }
        .form-section h3 { margin-top: 0; }
        input[type="text"], input[type="number"], select, button {
            padding: 10px;
            margin: 5px 0 10px 0;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button { background-color: #007bff; color: white; border: none; cursor: pointer; transition: background-color 0.3s ease; }
        button:hover { background-color: #0056b3; }
        .delete-btn { background-color: #dc3545; }
        .delete-btn:hover { background-color: #c82333; }
        .filter-section { margin-bottom: 20px; padding: 10px; background-color: #f0f0f0; border-radius: 5px; display: flex; gap: 20px; align-items: center; }
        .inline-form { display: inline-flex; align-items: center; gap: 5px; }
        .task-details-form { display: flex; gap: 5px; align-items: center; }
        .task-details-form input, .task-details-form select { padding: 5px; font-size: 0.9em; }
        .task-name { min-width: 150px; }
        .small-input { width: 60px; padding: 5px !important; }
        .room-header-controls { font-size: 0.9em; display: flex; align-items:center; gap: 5px; }
        .room-header-controls form { margin-bottom: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Household Chore Planner</h1>

        <div class="filter-section">
            <form method="GET" action="{{ url_for('index') }}" id="filterForm" class="inline-form">
                <label for="show_due_checkbox">Show only tasks that need to be done:</label>
                <input type="checkbox" id="show_due_checkbox" name="show_due" value="true" {% if show_only_due %}checked{% endif %} onchange="document.getElementById('filterForm').submit();">

                <label for="member_filter_select">Filter by member:</label>
                <select name="member_filter" id="member_filter_select" onchange="document.getElementById('filterForm').submit();">
                    <option value="all" {% if current_member_filter == 'all' %}selected{% endif %}>All Members</option>
                    <option value="unassigned" {% if current_member_filter == 'unassigned' %}selected{% endif %}>Unassigned</option>
                    {% for member_id, member in members.items() %}
                        <option value="{{ member_id }}" {% if current_member_filter == member_id %}selected{% endif %}>{{ member.name }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>

        <div class="form-section">
            <h3>Manage Family Members</h3>
            <form action="{{ url_for('add_member') }}" method="POST" class="inline-form">
                <input type="text" name="member_name" placeholder="New member name" required>
                <button type="submit">Add Member</button>
            </form>
            {% if members %}
            <h4>Existing Members:</h4>
            <ul>
                {% for member_id, member in members.items() %}
                <li>
                    {{ member.name }}
                    <form action="{{ url_for('delete_member', member_id=member_id) }}" method="POST" style="display: inline-block; margin-left: 10px;">
                        <button type="submit" class="delete-btn" onclick="return confirm('Are you sure you want to delete {{member.name}}? This will unassign their tasks.')">Delete</button>
                    </form>
                </li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>

        <div class="form-section">
            <h3>Add New Room</h3>
            <form action="{{ url_for('add_room') }}" method="POST" class="inline-form">
                <input type="text" name="room_name" placeholder="Room name" required>
                <input type="number" name="room_default_frequency" placeholder="Default Freq. (days)" value="7" min="1">
                <button type="submit">Add Room</button>
            </form>
        </div>

        <hr>

        {% for room_id, room in rooms.items() %}
            <div class="room">
                <h2>
                    <span>{{ room.name }}</span>
                    <span class="room-header-controls">
                        <form action="{{ url_for('update_room_frequency', room_id=room_id) }}" method="POST" class="inline-form">
                            <label for="room_freq_{{room_id}}">Default Task Freq (days):</label>
                            <input type="number" id="room_freq_{{room_id}}" name="room_frequency" value="{{ room.default_frequency_days if room.default_frequency_days is not none else '' }}" placeholder="e.g., 7" min="1" class="small-input">
                            <button type="submit" style="padding: 5px 8px;">Set</button>
                        </form>
                        <form action="{{ url_for('delete_room', room_id=room_id) }}" method="POST" class="inline-form">
                            <button type="submit" class="delete-btn" style="padding: 5px 8px;" onclick="return confirm('Are you sure you want to delete the room {{room.name}} and all its tasks?')">Delete Room</button>
                        </form>
                    </span>
                </h2>

                <div class="form-section" style="background-color: #fdfdfd; padding:10px; margin-top:10px;">
                    <h4>Add New Task to {{ room.name }}</h4>
                    <form action="{{ url_for('add_task', room_id=room_id) }}" method="POST" class="inline-form">
                        <input type="text" name="task_name" placeholder="Task description" required>
                        <input type="number" name="task_frequency" placeholder="Freq. (days, optional)" value="{{ room.default_frequency_days if room.default_frequency_days is not none else '' }}" min="1" class="small-input">
                        <button type="submit">Add Task</button>
                    </form>
                </div>

                {% if room.tasks %}
                    {% for task_id, task in room.tasks.items() %}
                        <div class="task {% if task.done %}done{% endif %}">
                            <form action="{{ url_for('toggle_task', room_id=room_id, task_id=task_id) }}" method="POST" style="display: inline-block;">
                                <input type="checkbox" id="task_{{ task_id }}" {% if task.done %}checked{% endif %} onchange="this.form.submit()">
                            </form>
                            <label for="task_{{ task_id }}" class="task-name">{{ task.name }}</label>

                            <div class="actions">
                                <form action="{{ url_for('update_task_frequency', room_id=room_id, task_id=task_id) }}" method="POST" class="task-details-form">
                                    <input type="number" name="task_frequency" value="{{ task.frequency_days if task.frequency_days is not none else '' }}" placeholder="Days" min="1" class="small-input" title="Task Frequency (days)">
                                    <button type="submit" style="padding: 5px 8px;">Set Freq</button>
                                </form>

                                <form action="{{ url_for('assign_task', room_id=room_id, task_id=task_id) }}" method="POST" class="task-details-form">
                                    <select name="member_id" onchange="this.form.submit()">
                                        <option value="unassign" {% if not task.assigned_to %}selected{% endif %}>Unassigned</option>
                                        {% for member_id_option, member in members.items() %}
                                            <option value="{{ member_id_option }}" {% if task.assigned_to == member_id_option %}selected{% endif %}>
                                                {{ member.name }}
                                            </option>
                                        {% endfor %}
                                    </select>
                                </form>
                                {% if task.assigned_to and members[task.assigned_to] %}
                                    <span class="assignment">Assigned to: {{ members[task.assigned_to].name }}</span>
                                {% elif task.assigned_to %}
                                     <span class="assignment">Assigned to: ID {{ task.assigned_to }} (Member not found)</span>
                                {% endif %}

                                {% if task.frequency_days %}
                                    <span class="frequency">Repeats every: {{ task.frequency_days }} day(s)</span>
                                {% endif %}
                                {% if task.last_done %}
                                    <span class="last-done">(Last done: {{ task.last_done }})</span>
                                {% endif %}
                                <form action="{{ url_for('delete_task', room_id=room_id, task_id=task_id) }}" method="POST" class="inline-form">
                                    <button type="submit" class="delete-btn" style="padding: 5px 8px;" onclick="return confirm('Are you sure you want to delete this task?')">Del Task</button>
                                </form>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>No tasks yet in {{ room.name }}.</p>
                {% endif %}
            </div>
        {% else %}
            <p>No rooms defined yet, or no tasks match current filters. Add a room to get started!</p>
        {% endfor %}
    </div>

    <script>
        // Simple script to ensure correct form submission for filters
        document.addEventListener('DOMContentLoaded', function () {
            const filterForm = document.getElementById('filterForm');
            const showDueCheckbox = document.getElementById('show_due_checkbox');
            const memberFilterSelect = document.getElementById('member_filter_select');

            // Store current query parameters
            const urlParams = new URLSearchParams(window.location.search);
            const memberFilterParam = urlParams.get('member_filter');

            // If show_due is checked, we need to ensure it's part of the form submission
            // If it's not checked, we don't want 'show_due=true' in the URL
            // The 'onchange' directly submits, this is more of a conceptual note for complex scenarios

            // Ensure member_filter is always part of the submission if set
            if (memberFilterParam && !filterForm.querySelector('[name="member_filter"]')) {
                let hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'member_filter';
                hiddenInput.value = memberFilterParam;
                filterForm.appendChild(hiddenInput);
            }
        });
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True)
