#include <Arduino.h>
#define ADC_PIN 34
// Number of samples to average
#define NUM_SAMPLES 2500
#define step 0.0024898648648649
void setup()
{
    Serial.begin(115200);
    Serial.println("Reading raw ADC...");
}
void loop()
{
    unsigned long sum = 0;
    // double vsum = 0;
    for (int i = 0; i < NUM_SAMPLES; ++i) {
        sum += analogRead(ADC_PIN);
    }
    float avg_adc = (float)sum / (float)NUM_SAMPLES;
    float voltage = avg_adc * step;
    // for (int i = 0; i < NUM_SAMPLES; ++i) {
    //     vsum += voltage;
    // }
    
    // float avg_volt = (float)vsum / (float)NUM_SAMPLES;
    Serial.print("Averaged Voltage: ");
    Serial.print(voltage,2 );
    Serial.println(" V");
    delay(1000);
}