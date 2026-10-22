cmake_minimum_required(VERSION 3.8)
project(solarbot_sim)
find_package(ament_cmake REQUIRED)

install(DIRECTORY models worlds launch config
  DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  scripts/brush_control.py
  scripts/cleaning_monitor.py
  scripts/place_droid.py
  DESTINATION lib/${PROJECT_NAME})

ament_package()
