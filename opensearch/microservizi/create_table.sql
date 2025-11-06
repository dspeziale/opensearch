-- Script per creare tabella di esempio employees

-- Elimina tabella se esiste
IF OBJECT_ID('dbo.employees', 'U') IS NOT NULL
    DROP TABLE dbo.employees;
GO

-- Crea tabella employees
CREATE TABLE dbo.employees (
    id INT PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(100) NOT NULL UNIQUE,
    department NVARCHAR(50),
    salary DECIMAL(10, 2),
    hire_date DATE,
    created_at DATETIME DEFAULT GETDATE(),
    updated_at DATETIME DEFAULT GETDATE()
);
GO

-- Crea indice su department per query più veloci
CREATE INDEX idx_employees_department ON dbo.employees(department);
GO

-- Inserisci dati di esempio
INSERT INTO dbo.employees (id, name, email, department, salary, hire_date)
VALUES
    (1, 'Mario Rossi', 'mario.rossi@example.com', 'IT', 50000.00, '2023-01-15'),
    (2, 'Laura Bianchi', 'laura.bianchi@example.com', 'HR', 45000.00, '2023-03-20'),
    (3, 'Giuseppe Verdi', 'giuseppe.verdi@example.com', 'Sales', 55000.00, '2022-11-10');
GO

-- Verifica inserimento
SELECT * FROM dbo.employees;
GO

-- Crea trigger per aggiornamento automatico di updated_at
CREATE TRIGGER trg_employees_update
ON dbo.employees
AFTER UPDATE
AS
BEGIN
    UPDATE dbo.employees
    SET updated_at = GETDATE()
    WHERE id IN (SELECT DISTINCT id FROM inserted);
END;
GO

PRINT 'Tabella employees creata con successo!';
