#include <iostream>
#include <string>
#include <vector>
#include <regex>

class ReportProcessor {
public:
    std::string sanitizeInput(const std::string& raw_input) {
        std::regex noise_patterns("(buenos días|oiga jefe|pucha que hace calor|saludos)");
        return std::regex_replace(raw_input, noise_patterns, "");
    }

    bool detectCriticalRisk(const std::string& text) {
        std::vector<std::string> risks = {"accidente", "lesion", "paralizacion", "huelga", "caida"};
        for (const auto& risk : risks) {
            if (text.find(risk) != std::string::npos) return true;
        }
        return false;
    }
};

int main() {
    ReportProcessor processor;
    std::string test_input = "buenos días jefe, tuvimos un accidente menor hoy al echar el cemento";
    
    std::cout << "--- PRUEBA DEL MOTOR C++ ---" << "\n";
    std::cout << "Input limpio: " << processor.sanitizeInput(test_input) << "\n";
    std::cout << "Riesgo detectado: " 
              << (processor.detectCriticalRisk(test_input) ? "Si [CRITICO]" : "No") << "\n";
    return 0;
}