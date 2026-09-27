// Analog joystick module -> USB serial, for the PolyDrive game (game_3d.py).
// Wiring:  VRx -> A0   VRy -> A1   SW -> D2   +5V -> 5V   GND -> GND
// Sends one line per ~16 ms:  x,y,button   (x, y = 0..1023, button = 1 when pressed)

const int PIN_X = A0;
const int PIN_Y = A1;
const int PIN_BUTTON = 2;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);   // the stick's button pulls the pin to GND when pressed
}

void loop() {
  int x = analogRead(PIN_X);
  int y = analogRead(PIN_Y);
  int pressed = digitalRead(PIN_BUTTON) == LOW ? 1 : 0;

  Serial.print(x);
  Serial.print(',');
  Serial.print(y);
  Serial.print(',');
  Serial.println(pressed);

  delay(16);
}
