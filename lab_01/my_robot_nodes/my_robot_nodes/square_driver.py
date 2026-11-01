#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry

from lab_interfaces.action import DriveDistance
from my_robot_interfaces.action import Rotate


class SquareDriver(Node):

    def __init__(self):
        super().__init__('square_driver')

        self.declare_parameter('side_length', 0.5)

        self.odom_received = False

        self.create_subscription(
            Odometry,
            '/odom',
            self.on_odom,
            10
        )

        self.drive_client = ActionClient(
            self, DriveDistance, '/drive_distance'
        )

        self.rotate_client = ActionClient(
            self, Rotate, '/rotate'
        )

    def on_odom(self, msg):
        self.odom_received = True

    def feedback_callback(self, feedback_msg):
        travelled = feedback_msg.feedback.travelled
        self.get_logger().info(
            f'Distance travelled: {travelled:.2f} m'
        )

    def send_drive_goal(self, distance):
        goal = DriveDistance.Goal()
        goal.distance = distance

        self.drive_client.wait_for_server()

        future = self.drive_client.send_goal_async(
            goal,
            feedback_callback=self.feedback_callback
        )

        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        return result_future.result().status == GoalStatus.STATUS_SUCCEEDED

    def send_rotate_goal(self, angle):
        goal = Rotate.Goal()
        goal.angle = angle

        self.rotate_client.wait_for_server()

        future = self.rotate_client.send_goal_async(goal)

        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()

        if not goal_handle.accepted:
            return False

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        return result_future.result().status == GoalStatus.STATUS_SUCCEEDED

    def drive_square(self):

        self.get_logger().info('Waiting for robot odometry...')

        while rclpy.ok() and not self.odom_received:
            rclpy.spin_once(self, timeout_sec=0.1)

        if not rclpy.ok():
            return

        self.get_logger().info('Robot is ready! Starting square.')

        side_length = self.get_parameter('side_length').value

        for side in range(1, 5):

            self.get_logger().info(f'Driving side {side}')

            if not self.send_drive_goal(side_length):
                self.get_logger().error(
                    f'Failed to drive side {side}. Stopping.'
                )
                return

            self.get_logger().info(
                f'Turning left after side {side}'
            )

            if not self.send_rotate_goal(math.pi / 2):
                self.get_logger().error(
                    f'Failed to turn after side {side}. Stopping.'
                )
                return

        self.get_logger().info('Square completed successfully!')


def main(args=None):
    rclpy.init(args=args)

    node = SquareDriver()

    try:
        node.drive_square()
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
