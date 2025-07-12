import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class TipoToken(Enum):
    """Tipos de tokens reconocidos"""
    TIPO_DATO = "TIPO_DATO"
    IDENTIFICADOR = "IDENTIFICADOR"
    NUMERO = "NUMERO"
    CADENA = "CADENA"
    BOOLEANO = "BOOLEANO"
    OPERADOR = "OPERADOR"
    ASIGNACION = "ASIGNACION"
    PALABRA_CLAVE = "PALABRA_CLAVE"
    PARENTESIS = "PARENTESIS"
    PUNTO_COMA = "PUNTO_COMA"
    DESCONOCIDO = "DESCONOCIDO"

@dataclass
class Token:
    """Representa un token del código fuente"""
    tipo: TipoToken
    valor: str
    linea: int
    columna: int

@dataclass
class Variable:
    """Representa una variable en la tabla de símbolos"""
    nombre: str
    tipo: str
    linea_declaracion: int
    inicializada: bool = False
    usada: bool = False

@dataclass
class Error:
    """Representa un error semántico"""
    tipo: str
    mensaje: str
    linea: int
    columna: int = 0

class AnalizadorLexico:
    """Analizador léxico para tokenizar el código fuente"""
    
    def __init__(self):
        self.patrones = [
            (TipoToken.TIPO_DATO, r'\b(int|float|double|bool|char|string|void)\b'),
            (TipoToken.PALABRA_CLAVE, r'\b(if|else|while|for|return|break|continue|switch|case|default)\b'),
            (TipoToken.BOOLEANO, r'\b(true|false)\b'),
            (TipoToken.NUMERO, r'\b\d+\.?\d*\b'),
            (TipoToken.CADENA, r'"[^"]*"'),
            (TipoToken.IDENTIFICADOR, r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
            (TipoToken.ASIGNACION, r'='),
            (TipoToken.OPERADOR, r'[+\-*/%<>=!&|]+'),
            (TipoToken.PARENTESIS, r'[(){}[\]]'),
            (TipoToken.PUNTO_COMA, r';'),
        ]
        
        self.patron_compilado = '|'.join(f'(?P<{tipo.name}>{patron})' for tipo, patron in self.patrones)
        self.regex = re.compile(self.patron_compilado)
    
    def tokenizar(self, codigo: str) -> List[Token]:
        """Convierte el código fuente en una lista de tokens"""
        tokens = []
        lineas = codigo.split('\n')
        
        for num_linea, linea in enumerate(lineas, 1):
            linea = linea.strip()
            if not linea or linea.startswith('//'):
                continue
                
            for match in self.regex.finditer(linea):
                tipo_token = TipoToken[match.lastgroup]
                valor = match.group()
                columna = match.start()
                
                tokens.append(Token(tipo_token, valor, num_linea, columna))
        
        return tokens

class AnalizadorSemantico:
    """Analizador semántico principal"""
    
    def __init__(self):
        self.tabla_simbolos: Dict[str, Variable] = {}
        self.errores: List[Error] = []
        self.advertencias: List[Error] = []
        self.tokens: List[Token] = []
        self.posicion = 0
        
        # Tipos de datos válidos
        self.tipos_validos = {'int', 'float', 'double', 'bool', 'char', 'string', 'void'}
        
        # Operadores de compatibilidad
        self.compatibilidad_tipos = {
            'int': ['int', 'float', 'double'],
            'float': ['float', 'double'],
            'double': ['double'],
            'bool': ['bool'],
            'char': ['char'],
            'string': ['string']
        }
    
    def analizar(self, codigo: str) -> str:
        """Método principal para analizar el código"""
        # Limpiar estado anterior
        self.limpiar_estado()
        
        # Tokenizar el código
        analizador_lexico = AnalizadorLexico()
        self.tokens = analizador_lexico.tokenizar(codigo)
        
        if not self.tokens:
            self.errores.append(Error("ERROR", "No se encontraron tokens válidos", 1))
            return self.generar_reporte()
        
        # Analizar semánticamente
        self.analizar_tokens()
        
        # Verificaciones adicionales
        self.verificar_variables_no_usadas()
        self.verificar_variables_no_inicializadas()
        
        return self.generar_reporte()
    
    def limpiar_estado(self):
        """Limpia el estado del analizador"""
        self.tabla_simbolos.clear()
        self.errores.clear()
        self.advertencias.clear()
        self.tokens.clear()
        self.posicion = 0
    
    def analizar_tokens(self):
        """Analiza la secuencia de tokens"""
        while self.posicion < len(self.tokens):
            token_actual = self.tokens[self.posicion]
            
            if token_actual.tipo == TipoToken.TIPO_DATO:
                self.analizar_declaracion()
            elif token_actual.tipo == TipoToken.IDENTIFICADOR:
                self.analizar_identificador()
            elif token_actual.tipo == TipoToken.PALABRA_CLAVE:
                self.analizar_palabra_clave()
            else:
                self.posicion += 1
    
    def analizar_declaracion(self):
        """Analiza una declaración de variable"""
        if self.posicion >= len(self.tokens):
            return
        
        token_tipo = self.tokens[self.posicion]
        self.posicion += 1
        
        if self.posicion >= len(self.tokens):
            self.errores.append(Error("ERROR", f"Declaración incompleta en línea {token_tipo.linea}", token_tipo.linea))
            return
        
        token_nombre = self.tokens[self.posicion]
        
        if token_nombre.tipo != TipoToken.IDENTIFICADOR:
            self.errores.append(Error("ERROR", f"Se esperaba un identificador después de '{token_tipo.valor}' en línea {token_tipo.linea}", token_tipo.linea))
            return
        
        # Verificar si la variable ya existe
        if token_nombre.valor in self.tabla_simbolos:
            self.errores.append(Error("ERROR", f"Variable '{token_nombre.valor}' ya declarada en línea {token_nombre.linea}", token_nombre.linea))
            return
        
        # Agregar variable a la tabla de símbolos
        variable = Variable(token_nombre.valor, token_tipo.valor, token_nombre.linea)
        self.tabla_simbolos[token_nombre.valor] = variable
        
        self.posicion += 1
        
        # Verificar si hay inicialización
        if self.posicion < len(self.tokens) and self.tokens[self.posicion].tipo == TipoToken.ASIGNACION:
            self.analizar_inicializacion(variable)
    
    def analizar_inicializacion(self, variable: Variable):
        """Analiza la inicialización de una variable"""
        self.posicion += 1  # Saltar el '='
        
        if self.posicion >= len(self.tokens):
            self.errores.append(Error("ERROR", f"Inicialización incompleta para variable '{variable.nombre}' en línea {variable.linea_declaracion}", variable.linea_declaracion))
            return
        
        token_valor = self.tokens[self.posicion]
        
        # Verificar compatibilidad de tipos
        if self.verificar_compatibilidad_tipos(variable.tipo, token_valor):
            variable.inicializada = True
        else:
            self.errores.append(Error("ERROR", f"Tipo incompatible en inicialización de '{variable.nombre}' en línea {variable.linea_declaracion}", variable.linea_declaracion))
        
        self.posicion += 1
    
    def analizar_identificador(self):
        """Analiza un identificador (uso de variable)"""
        token_identificador = self.tokens[self.posicion]
        
        # Verificar si la variable está declarada
        if token_identificador.valor not in self.tabla_simbolos:
            self.errores.append(Error("ERROR", f"Variable '{token_identificador.valor}' no declarada en línea {token_identificador.linea}", token_identificador.linea))
        else:
            # Marcar como usada
            self.tabla_simbolos[token_identificador.valor].usada = True
            
            # Verificar si se está asignando valor
            if self.posicion + 1 < len(self.tokens) and self.tokens[self.posicion + 1].tipo == TipoToken.ASIGNACION:
                self.posicion += 1  # Ir al '='
                self.analizar_asignacion(token_identificador.valor)
                return
        
        self.posicion += 1
    
    def analizar_asignacion(self, nombre_variable: str):
        """Analiza una asignación a una variable existente"""
        self.posicion += 1  # Saltar el '='
        
        if self.posicion >= len(self.tokens):
            self.errores.append(Error("ERROR", f"Asignación incompleta a variable '{nombre_variable}'", self.tokens[self.posicion-1].linea))
            return
        
        token_valor = self.tokens[self.posicion]
        variable = self.tabla_simbolos[nombre_variable]
        
        # Verificar compatibilidad de tipos
        if self.verificar_compatibilidad_tipos(variable.tipo, token_valor):
            variable.inicializada = True
        else:
            self.errores.append(Error("ERROR", f"Tipo incompatible en asignación a '{nombre_variable}' en línea {token_valor.linea}", token_valor.linea))
        
        self.posicion += 1
    
    def analizar_palabra_clave(self):
        """Analiza palabras clave como if, while, etc."""
        token_palabra = self.tokens[self.posicion]
        
        if token_palabra.valor in ['if', 'while', 'for']:
            # Buscar condición entre paréntesis
            self.analizar_estructura_control(token_palabra)
        
        self.posicion += 1
    
    def analizar_estructura_control(self, token_palabra: Token):
        """Analiza estructuras de control"""
        # Buscar paréntesis de apertura
        parentesis_encontrado = False
        pos_temp = self.posicion + 1
        
        while pos_temp < len(self.tokens):
            if self.tokens[pos_temp].tipo == TipoToken.PARENTESIS and self.tokens[pos_temp].valor == '(':
                parentesis_encontrado = True
                break
            pos_temp += 1
        
        if not parentesis_encontrado:
            self.errores.append(Error("ERROR", f"Se esperaba '(' después de '{token_palabra.valor}' en línea {token_palabra.linea}", token_palabra.linea))
    
    def verificar_compatibilidad_tipos(self, tipo_variable: str, token_valor: Token) -> bool:
        """Verifica si un valor es compatible con un tipo de variable"""
        if token_valor.tipo == TipoToken.NUMERO:
            if '.' in token_valor.valor:
                return tipo_variable in ['float', 'double']
            else:
                return tipo_variable in ['int', 'float', 'double']
        
        elif token_valor.tipo == TipoToken.BOOLEANO:
            return tipo_variable == 'bool'
        
        elif token_valor.tipo == TipoToken.CADENA:
            return tipo_variable == 'string'
        
        elif token_valor.tipo == TipoToken.IDENTIFICADOR:
            # Verificar si es una variable del mismo tipo
            if token_valor.valor in self.tabla_simbolos:
                tipo_origen = self.tabla_simbolos[token_valor.valor].tipo
                return tipo_origen in self.compatibilidad_tipos.get(tipo_variable, [])
            return False
        
        return False
    
    def verificar_variables_no_usadas(self):
        """Detecta variables declaradas pero no usadas"""
        for variable in self.tabla_simbolos.values():
            if not variable.usada:
                self.advertencias.append(Error("ADVERTENCIA", f"Variable '{variable.nombre}' declarada pero no usada", variable.linea_declaracion))
    
    def verificar_variables_no_inicializadas(self):
        """Detecta variables usadas pero no inicializadas"""
        for variable in self.tabla_simbolos.values():
            if variable.usada and not variable.inicializada:
                self.advertencias.append(Error("ADVERTENCIA", f"Variable '{variable.nombre}' usada sin inicializar", variable.linea_declaracion))
    
    def generar_reporte(self) -> str:
        """Genera el reporte final del análisis"""
        reporte = []
        reporte.append("=" * 50)
        reporte.append("REPORTE DE ANÁLISIS SEMÁNTICO")
        reporte.append("=" * 50)
        
        # Tabla de símbolos
        if self.tabla_simbolos:
            reporte.append("\n📋 TABLA DE SÍMBOLOS:")
            reporte.append("-" * 30)
            for nombre, variable in self.tabla_simbolos.items():
                estado = "✓ Inicializada" if variable.inicializada else "⚠ No inicializada"
                uso = "✓ Usada" if variable.usada else "⚠ No usada"
                reporte.append(f"{nombre:<15} | {variable.tipo:<8} | Línea {variable.linea_declaracion:<3} | {estado} | {uso}")
        
        # Errores
        if self.errores:
            reporte.append(f"\n❌ ERRORES ENCONTRADOS ({len(self.errores)}):")
            reporte.append("-" * 30)
            for error in self.errores:
                reporte.append(f"Línea {error.linea}: {error.mensaje}")
        
        # Advertencias
        if self.advertencias:
            reporte.append(f"\n⚠️ ADVERTENCIAS ({len(self.advertencias)}):")
            reporte.append("-" * 30)
            for advertencia in self.advertencias:
                reporte.append(f"Línea {advertencia.linea}: {advertencia.mensaje}")
        
        # Resumen
        reporte.append(f"\n📊 RESUMEN:")
        reporte.append("-" * 20)
        reporte.append(f"Variables declaradas: {len(self.tabla_simbolos)}")
        reporte.append(f"Errores: {len(self.errores)}")
        reporte.append(f"Advertencias: {len(self.advertencias)}")
        reporte.append(f"Tokens procesados: {len(self.tokens)}")
        
        if self.errores:
            reporte.append("\n❌ ANÁLISIS COMPLETADO CON ERRORES")
        else:
            reporte.append("\n✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        
        return "\n".join(reporte)

def main():
    """Función principal para probar el analizador"""
    # Código de ejemplo para probar
    codigo_ejemplo = """
    int x = 5;
    float precio = 19.99;
    string nombre = "Juan";
    bool activo = true;
    int y;
    
    if (x > 0) {
        y = x + 1;
    }
    
    int z = x + y;
    float descuento = precio * 0.1;
    """
    
    print("ANALIZADOR SEMÁNTICO EN PYTHON")
    print("=" * 40)
    print("Código a analizar:")
    print(codigo_ejemplo)
    print("\n" + "=" * 40)
    
    # Crear analizador y ejecutar
    analizador = AnalizadorSemantico()
    resultado = analizador.analizar(codigo_ejemplo)
    
    print(resultado)
    
    # Ejemplo interactivo
    print("\n" + "=" * 40)
    print("¿Deseas probar con tu propio código? (s/n)")
    respuesta = input().lower()
    
    if respuesta == 's':
        print("Ingresa tu código (presiona Enter dos veces para finalizar):")
        lineas = []
        while True:
            linea = input()
            if linea == "" and len(lineas) > 0 and lineas[-1] == "":
                break
            lineas.append(linea)
        
        codigo_usuario = "\n".join(lineas)
        resultado_usuario = analizador.analizar(codigo_usuario)
        print("\n" + resultado_usuario)

if __name__ == "__main__":
    main()