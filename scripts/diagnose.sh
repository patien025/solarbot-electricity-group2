#!/usr/bin/env bash
# Run in a 2nd terminal WHILE the simulation is running (source ROS + the workspace first).
# It tells us whether the droid, the ROS bridge, or the keyboard node is the problem.
pose() { gz topic -e -t /model/solarbot/pose -n 1 2>/dev/null | grep -A4 'position' | head -5 | tr -d '\n'; echo; }

echo "== 1. Gazebo topics for the droid =="
gz topic -l | grep -E "^/(cmd_vel|odom|brush_cmd|tf)$|/model/solarbot" || echo "NONE FOUND -> droid plugins not loaded (is the world running / unpaused?)"

echo; echo "== 2. ROS topics =="
ros2 topic list | grep -E "cmd_vel|odom|brush|joint_states|solarbot" || echo "NONE FOUND -> bridge not running"

echo; echo "== 3. Droid position before =="; pose

echo; echo "== 4. Drive straight through GAZEBO (no ROS involved) for 4 s =="
gz topic -t /cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.2}'
sleep 4
pose
gz topic -t /cmd_vel -m gz.msgs.Twist -p 'linear: {x: 0.0}'

echo; echo "== 5. Drive through ROS (bridge path) for 4 s =="
timeout 4 ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: -0.2}}" > /dev/null
pose
echo; echo "Who listens to /cmd_vel on the ROS side:"; ros2 topic info /cmd_vel 2>/dev/null
echo; echo "If the position changed in step 4 but not step 5 -> bridge problem."
echo "If it changed in neither -> droid/physics problem. Send me this whole output."
