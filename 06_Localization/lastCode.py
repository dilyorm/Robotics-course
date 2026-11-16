import sys
import time
import random
import math

class Program():
  __interpretation_started_timestamp__ = time.time() * 1000

  pi = 3.141592653589793
  B = None
  X_ref = None
  Y_ref = None
  bearing = None
  control_l = None
  control_r = None
  course = None
  courseAngle = None
  course_gyro = None
  course_odom = None
  distance = None
  gyro = None
  gyro_inc = None
  i = None
  path = None
  prev_path = None
  prev_time = None
  r = None
  str = None
  t = None
  theta_l = None
  theta_r = None
  threshold = None
  x = None
  y = None

  def execMain(self):

    
    brick.encoder("E3").reset()
    brick.encoder("E4").reset()
    
    script.removeFile("trajectory_data.txt")
    
    brick.marker().down("blue")
    
    self.x = 0.0
    self.y = 0.0
    self.path = 0.0
    self.i = 0
    self.course = 0.0
    self.course_gyro = 0.0
    self.course_odom = 0.0
    self.theta_l = brick.encoder("E3").read()
    self.theta_r = brick.encoder("E4").read()
    self.prev_time = (time.time() * 1000 - self.__interpretation_started_timestamp__)
    self.r = 0.042
    self.B = 0.194
    self.X_ref = [ 0.5, 0.5, 0, 0 ]
    self.Y_ref = [ 0, 0.5, 0.5, 0 ]
    self.threshold = 0.05
    self.distance = 100.0
    self.gyro = brick.gyroscope().read()[2]
    self.gyro_inc = 0.0
    self.courseAngle = 0.0
    
    while self.i < 4:
      
      while self.distance > self.threshold:
        self.gyro = brick.gyroscope().read()[2]
        self.t = (time.time() * 1000 - self.__interpretation_started_timestamp__)
        self.course_gyro = self.course_gyro + self.gyro / 1000 * (self.t - self.prev_time) / 1000 * self.pi / 180
        self.gyro_inc = self.gyro / 1000 * (self.t - self.prev_time) / 1000 * self.pi / 180
        self.prev_time = self.t
        self.theta_l = brick.encoder("E4").read() * self.pi / 180
        self.theta_r = brick.encoder("E3").read() * self.pi / 180
        self.prev_path = self.path
        self.path = (self.theta_r + self.theta_l) * self.r / 2
        self.course_odom = (self.theta_r - self.theta_l) * self.r / self.B
        self.course = 0.01 * self.course_odom + 0.99 * (self.course + self.gyro_inc)
        self.x = self.x + (self.path - self.prev_path) * math.cos(self.course)
        self.y = self.y + (self.path - self.prev_path) * math.sin(self.course)
        self.distance = math.sqrt(math.pow((self.X_ref[self.i] - self.x), 2) + math.pow((self.Y_ref[self.i] - self.y), 2))
        self.bearing = math.atan2(self.Y_ref[self.i] - self.y, self.X_ref[self.i] - self.x)
        self.courseAngle = self.bearing - self.course
        self.courseAngle = self.courseAngle - 2 * self.pi * math.floor((self.courseAngle + self.pi) / (2 * self.pi))
        self.control_l = (30 * self.distance + 20) * math.cos(self.courseAngle) - 50 * self.courseAngle
        self.control_r = (30 * self.distance + 20) * math.cos(self.courseAngle) + 50 * self.courseAngle
        self.str = str(self.theta_l) + "," + str(self.theta_r) + "," + str(self.gyro) + "," + str(self.t) + "\n"
        brick.motor("M3").setPower(int(self.control_r))
        
        brick.motor("M4").setPower(int(self.control_l))
        
        script.writeToFile("trajectory_data.txt", self.str)
        
        script.wait(5)
        
      self.i = self.i + 1
      self.distance = 100
    brick.stop()
    return

def main():
  program = Program()
  program.execMain()

if __name__ == '__main__':
  main()
