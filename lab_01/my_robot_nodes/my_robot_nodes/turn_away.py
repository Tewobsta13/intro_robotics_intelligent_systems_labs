import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_srvs.srv import SetBool
from lab_interfaces.msg import ObstacleInfo

from my_robot_interfaces.msg import RobotStatus
from my_robot_interfaces.srv import SetTurnSpeed


class TurnAway(Node):
    def __init__(self):
        super().__init__('turn_away')

        # Parameters
        self.declare_parameter('forward_speed', 0.2)
        self.declare_parameter('turn_speed', 0.5)
        self.declare_parameter('max_turn_speed', 1.5)

        # Robot starts disabled
        self.enabled = False

        # Publishers
        self.publisher = self.create_publisher(
            Twist, '/cmd_vel', 10
        )

        self.status_publisher = self.create_publisher(
            RobotStatus, '/robot_status', 10
        )

        # Subscriber
        self.subscription = self.create_subscription(
            ObstacleInfo,
            '/obstacle',
            self.on_obstacle,
            10
        )

        # Enable/disable service
        self.enable_service = self.create_service(
            SetBool,
            '/turn_away_enable',
            self.enable_callback
        )

        # Set turning speed service
        self.speed_service = self.create_service(
            SetTurnSpeed,
            '/set_turn_speed',
            self.speed_callback
        )

    def enable_callback(self, request, response):
        self.enabled = request.data

        if not self.enabled:
            # Stop robot immediately when disabled
            self.publisher.publish(Twist())
            self.publish_status('stopped', 0.0)

        response.success = True
        response.message = (
            'Robot enabled' if self.enabled else 'Robot disabled'
        )

        self.get_logger().info(response.message)
        return response

    def speed_callback(self, request, response):
        speed = request.turn_speed
        max_speed = self.get_parameter('max_turn_speed').value

        if speed <= 0.0 or speed > max_speed:
            response.success = False
            response.message = (
                f'Speed must be greater than 0 and at most {max_speed}'
            )
        else:
            self.set_parameters([
                rclpy.parameter.Parameter(
                    'turn_speed',
                    rclpy.Parameter.Type.DOUBLE,
                    float(speed)
                )
            ])

            response.success = True
            response.message = f'Turn speed updated to {speed}'

        self.get_logger().info(response.message)
        return response

    def publish_status(self, state, distance):
        status = RobotStatus()
        status.state = state
        status.obstacle_distance = distance
        self.status_publisher.publish(status)

    def on_obstacle(self, msg):
        twist = Twist()

        if not self.enabled:
            self.publish_status('stopped', msg.distance)
            return

        forward_speed = self.get_parameter('forward_speed').value
        turn_speed = self.get_parameter('turn_speed').value

        if not msg.too_close:
            twist.linear.x = forward_speed
            state = 'forward'
        else:
            twist.angular.z = (
                -turn_speed if msg.angle > 0 else turn_speed
            )
            state = 'turning'

        self.publisher.publish(twist)
        self.publish_status(state, msg.distance)


def main(args=None):
    rclpy.init(args=args)
    node = TurnAway()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
