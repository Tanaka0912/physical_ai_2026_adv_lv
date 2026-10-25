#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/pose.pb.h>
#include <gz/transport/Node.hh>

#include <iostream>
#include <sstream>
#include <string>

int main() {
  gz::transport::Node node;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream input(line);
    double x, y, z, qx, qy, qz, qw;
    if (!(input >> x >> y >> z >> qx >> qy >> qz >> qw)) {
      std::cerr << "Ignoring invalid pose line\n";
      continue;
    }
    gz::msgs::Pose request;
    request.set_name("red_cylinder");
    request.mutable_position()->set_x(x);
    request.mutable_position()->set_y(y);
    request.mutable_position()->set_z(z);
    request.mutable_orientation()->set_x(qx);
    request.mutable_orientation()->set_y(qy);
    request.mutable_orientation()->set_z(qz);
    request.mutable_orientation()->set_w(qw);
    gz::msgs::Boolean reply;
    bool result = false;
    const bool received = node.Request("/world/default/set_pose", request, 500u,
                                       reply, result);
    if (!received || !result || !reply.data()) {
      std::cerr << "Gazebo set_pose failed\n";
    }
  }
}
