class InstructionSet:
    def __init__(self, step, opcode, dest_reg, clkcyc, src_reg=None, src_reg2=None, immediate_val=0):
        self.step = step
        self.opcode = opcode
        self.dest_reg = dest_reg
        self.src_reg = src_reg
        self.src_reg2 = src_reg2
        self.immediate = immediate_val
        self.clkcyc = clkcyc

    def six_bit_opcode(self):
        opcode_map = {
            "mov": "000001",
            "add": "000010",
            "sub": "000011",
            "mul": "000100",
            "div": "000101"
        }
        return opcode_map.get(self.opcode, "000000")

    def encode_32_bit_instruction(self):
        op_bits = self.six_bit_opcode()
        rd_bits = self.dest_reg.to_5_bit_adr()

        if self.src_reg2:
            # R-type: opcode(6) | rd(5) | rs1(5) | rs2(5) | unused(11)
            rs1_bits = self.src_reg.to_5_bit_adr() if self.src_reg else "00000"
            rs2_bits = self.src_reg2.to_5_bit_adr()
            unused = "00000000000"
            return f"{op_bits} {rd_bits} {rs1_bits} {rs2_bits} {unused}"
        else:
            # I-type: opcode(6) | rd(5) | rs(5) | imm(16)
            rs_bits = self.src_reg.to_5_bit_adr() if self.src_reg else "00000"
            # FIX: was missing the else branch for negative immediates when src_reg present.
            # Now always encode immediate correctly regardless of src_reg.
            if self.src_reg and not self.src_reg2:
                # Register-to-register (e.g. mov r1 r2, add r1 r2): imm field is 0
                imm_bits = format(0, '016b')
            elif self.immediate >= 0:
                imm_bits = format(self.immediate, '016b')
            else:
                imm_bits = bin(self.immediate & 0xFFFF)[2:].zfill(16)
            return f"{op_bits} {rd_bits} {rs_bits} {imm_bits}"

    def __str__(self):
        instruction_str = f"{self.opcode} {self.dest_reg.get_reg_name()}"
        if self.src_reg2:
            instruction_str += f", {self.src_reg.get_reg_name()}, {self.src_reg2.get_reg_name()}"
        elif self.src_reg:
            instruction_str += f", {self.src_reg.get_reg_name()}"
        else:
            instruction_str += f", {self.immediate}"

        encoded = self.encode_32_bit_instruction()
        return f"[{self.step:<2}] {instruction_str:<20} | {encoded} | {self.clkcyc} cycles"


class Registers:
    def __init__(self, reg_val, reg_name):
        self.reg_val = reg_val
        self.reg_name = reg_name
        self.reg_adr_num = int(reg_name[1:])

    def get_reg_name(self):
        return self.reg_name

    def set_reg_val(self, reg_val):
        self.reg_val = reg_val

    def get_reg_val(self):
        return self.reg_val

    def to_32_bit_val(self):
        if self.reg_val >= 0:
            return format(self.reg_val, '032b')
        else:
            return bin(self.reg_val & 0xFFFFFFFF)[2:].zfill(32)

    def to_5_bit_adr(self):
        return format(self.reg_adr_num, '05b')


if __name__ == "__main__":
    regs = {f"r{i}": Registers(0, f"r{i}") for i in range(32)}
    steps = []
    step = 0

    print("--- 32-Bit ISA CPU Simulator (With Data Hazards) ---")
    print("2-operand: <opcode> <dest> <src/imm>       e.g. mov r1 10, add r1 r2")
    print("3-operand: <opcode> <dest> <src1> <src2>   e.g. add r3 r1 r2")
    print("Type 'end 0 0' to run.")
    print("-" * 52)

    while True:
        instruction = input(f"PC[{step}] > ").strip().lower()
        if instruction == "end 0 0":
            break

        input_list = instruction.split()
        if len(input_list) not in (3, 4):
            print("Invalid format. Use: opcode dest src/imm  OR  opcode dest src1 src2")
            continue

        opcode = input_list[0]
        dest_reg_name = input_list[1]

        if dest_reg_name not in regs:
            print(f"Invalid destination register: {dest_reg_name}")
            continue

        dest_reg = regs[dest_reg_name]
        valid_opcodes = {"mov", "add", "sub", "mul", "div"}
        if opcode not in valid_opcodes:
            print(f"Invalid opcode: {opcode}. Supported: mov, add, sub, mul, div")
            continue

        if len(input_list) == 4:
            src1_name = input_list[2]
            src2_name = input_list[3]

            if src1_name not in regs or src2_name not in regs:
                print("Invalid source register.")
                continue

            src1 = regs[src1_name]
            src2 = regs[src2_name]

            if opcode == "mov":
                print("Error: mov does not support 3-operand format.")
                continue
            elif opcode == "add":
                dest_reg.set_reg_val(src1.get_reg_val() + src2.get_reg_val())
                steps.append(InstructionSet(step, opcode, dest_reg, 2, src_reg=src1, src_reg2=src2))
            elif opcode == "sub":
                dest_reg.set_reg_val(src1.get_reg_val() - src2.get_reg_val())
                steps.append(InstructionSet(step, opcode, dest_reg, 3, src_reg=src1, src_reg2=src2))
            elif opcode == "mul":
                dest_reg.set_reg_val(src1.get_reg_val() * src2.get_reg_val())
                steps.append(InstructionSet(step, opcode, dest_reg, 4, src_reg=src1, src_reg2=src2))
            elif opcode == "div":
                if src2.get_reg_val() == 0:
                    print("Error: Division by zero.")
                    continue
                dest_reg.set_reg_val(src1.get_reg_val() // src2.get_reg_val())
                steps.append(InstructionSet(step, opcode, dest_reg, 4, src_reg=src1, src_reg2=src2))
        else:
            operand2 = input_list[2]
            try:
                value = int(operand2)
                if opcode == "mov":
                    dest_reg.set_reg_val(value)
                    steps.append(InstructionSet(step, opcode, dest_reg, 1, immediate_val=value))
                elif opcode == "add":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() + value)
                    steps.append(InstructionSet(step, opcode, dest_reg, 2, immediate_val=value))
                elif opcode == "sub":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() - value)
                    steps.append(InstructionSet(step, opcode, dest_reg, 3, immediate_val=value))
                elif opcode == "mul":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() * value)
                    steps.append(InstructionSet(step, opcode, dest_reg, 4, immediate_val=value))
                elif opcode == "div":
                    if value == 0:
                        print("Error: Division by zero.")
                        continue
                    dest_reg.set_reg_val(dest_reg.get_reg_val() // value)
                    steps.append(InstructionSet(step, opcode, dest_reg, 4, immediate_val=value))
            except ValueError:
                if operand2 not in regs:
                    print(f"Invalid source register: {operand2}")
                    continue

                src_reg = regs[operand2]
                if opcode == "mov":
                    dest_reg.set_reg_val(src_reg.get_reg_val())
                    steps.append(InstructionSet(step, opcode, dest_reg, 1, src_reg=src_reg))
                elif opcode == "add":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() + src_reg.get_reg_val())
                    steps.append(InstructionSet(step, opcode, dest_reg, 2, src_reg=src_reg))
                elif opcode == "sub":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() - src_reg.get_reg_val())
                    steps.append(InstructionSet(step, opcode, dest_reg, 3, src_reg=src_reg))
                elif opcode == "mul":
                    dest_reg.set_reg_val(dest_reg.get_reg_val() * src_reg.get_reg_val())
                    steps.append(InstructionSet(step, opcode, dest_reg, 4, src_reg=src_reg))
                elif opcode == "div":
                    if src_reg.get_reg_val() == 0:
                        print("Error: Division by zero.")
                        continue
                    dest_reg.set_reg_val(dest_reg.get_reg_val() // src_reg.get_reg_val())
                    steps.append(InstructionSet(step, opcode, dest_reg, 4, src_reg=src_reg))
        step += 1

    if not steps:
        print("No instructions entered.")
        exit()

    print("\n" + "=" * 70)
    print(f"{'PC':<5} {'Decoded':<22} {'32-Bit Encoded Machine Code':<40} {'Cost'}")
    print("=" * 70)
    for s in steps:
        print(s)

    print("\n--- Final Register States (Non-Zero) ---")
    for name, reg in regs.items():
        if reg.get_reg_val() != 0:
            print(f"{name:<4} = {reg.get_reg_val():<5} [{reg.to_32_bit_val()}]")

    num_instructions = len(steps)

    # --- PIPELINE HAZARD DETECTION ---
    start_cycles = []
    stalls_count = 0

    for i in range(num_instructions):
        if i == 0:
            start_cycles.append(1)
            continue

        curr = steps[i]

        # Build the set of registers this instruction reads at the ID stage.
        reads = set()
        if curr.src_reg:
            reads.add(curr.src_reg.get_reg_name())
        if curr.src_reg2:
            reads.add(curr.src_reg2.get_reg_name())
        # FIX: 2-operand ALU ops implicitly read their destination register
        # (e.g. "add r1 5" means r1 = r1 + 5, so r1 is both read and written).
        if curr.opcode in {"add", "sub", "mul", "div"} and not curr.src_reg2:
            reads.add(curr.dest_reg.get_reg_name())

        earliest_start = start_cycles[i - 1] + 1

        for j in range(i):
            prev = steps[j]
            prev_start = start_cycles[j]

            # --- 1. RAW (Read-After-Write) hazard ---
            # The consumer reads at its ID stage (cycle: curr_start + 1).
            # The producer writes back at its WB stage (cycle: prev_start + prev.clkcyc + 2).
            # With half-cycle internal forwarding: consumer ID can coincide with producer WB.
            #   curr_start + 1 >= prev_start + prev.clkcyc + 2
            #   => curr_start >= prev_start + prev.clkcyc + 1
            if prev.dest_reg.get_reg_name() in reads:
                required_raw_start = prev_start + prev.clkcyc + 1
                if required_raw_start > earliest_start:
                    earliest_start = required_raw_start

            # --- 2. WAW (Write-After-Write) hazard ---
            # The later instruction must not retire (WB) before the earlier one.
            # prev WB ends at: prev_start + prev.clkcyc + 2
            # curr WB ends at: curr_start + curr.clkcyc + 2
            # Require: curr WB end > prev WB end
            #   curr_start + curr.clkcyc + 2 > prev_start + prev.clkcyc + 2
            #   => curr_start > prev_start + prev.clkcyc - curr.clkcyc
            #   => curr_start >= prev_start + prev.clkcyc - curr.clkcyc + 1
            # FIX: clamp to at least (prev_start + 1) so the formula never
            # relaxes the constraint below what sequential issue already gives.
            if prev.dest_reg.get_reg_name() == curr.dest_reg.get_reg_name():
                required_waw_start = max(
                    prev_start + 1,
                    prev_start + prev.clkcyc - curr.clkcyc + 1
                )
                if required_waw_start > earliest_start:
                    earliest_start = required_waw_start

            # --- 3. Structural hazard (single unpipelined ALU) ---
            # The previous instruction's EX stage occupies cycles:
            #   [prev_start + 2 .. prev_start + prev.clkcyc + 1]  (inclusive)
            # The current instruction's EX stage starts at: curr_start + 2
            # They must not overlap:
            #   curr_start + 2 > prev_start + prev.clkcyc + 1
            #   => curr_start >= prev_start + prev.clkcyc
            required_struct_start = prev_start + prev.clkcyc
            if required_struct_start > earliest_start:
                earliest_start = required_struct_start

        # Stalls = extra cycles beyond back-to-back issue
        ideal_start = start_cycles[i - 1] + 1
        stalls_count += earliest_start - ideal_start
        start_cycles.append(earliest_start)

    # --- Metrics ---
    unpipelined_clk_cycs = sum(s.clkcyc + 3 for s in steps)
    unpipelined_cpi = unpipelined_clk_cycs / num_instructions

    # WB of instruction i ends at: start_cycles[i] + steps[i].clkcyc + 2
    pipelined_clk_cycs = max(
        start_cycles[i] + steps[i].clkcyc + 2 for i in range(num_instructions)
    )
    pipelined_cpi = pipelined_clk_cycs / num_instructions
    speedup = unpipelined_clk_cycs / pipelined_clk_cycs

    print("\n--- Performance Metrics ---")
    print(f"Total Instructions     = {num_instructions}")
    print(f"{'':25} {'Unpipelined':>12}  {'Pipelined':>12}")
    print(f"{'Total Clock Cycles':25} {unpipelined_clk_cycs:>12}  {pipelined_clk_cycs:>12}")
    print(f"{'Data Hazards (Stalls)':25} {'0':>12}  {stalls_count:>12}")
    print(f"{'Average CPI':25} {unpipelined_cpi:>12.2f}  {pipelined_cpi:>12.2f}")
    print(f"{'Speedup':25} {speedup:>12.2f}x")

    # --- Pipelined Execution Trace ---
    # FIX: use absolute cycle offsets from cycle 1 for every row so that
    # columns stay aligned with the header regardless of accumulated stalls.
    COL = 5  # characters per cycle column

    print("\n--- Pipelined Execution Trace (with Hazard Stalls) ---")

    # Header: cycle numbers aligned to COL-wide columns
    label_width = 12          # "[N ] op rd :" prefix
    print(" " * label_width, end="")
    for x in range(1, pipelined_clk_cycs + 1):
        print(f" C{x:<{COL - 2}}", end="")
    print()

    for i, s in enumerate(steps):
        start = start_cycles[i]
        instr_label = f"[{s.step:<2}] {s.opcode} {s.dest_reg.get_reg_name():<4}:"
        print(f"{instr_label:<{label_width}}", end="")

        # FIX: track absolute column position (1-based cycle number) and
        # advance it by printing blanks or stage tokens as needed.
        col_pos = 1  # next cycle we will print into

        # Empty space before IF (stalls or idle cycles)
        while col_pos < start:
            print(" " * COL, end="")
            col_pos += 1

        # IF stage (1 cycle)
        print(f"{'IF':^{COL}}", end="")
        col_pos += 1

        # ID stage (1 cycle)
        print(f"{'ID':^{COL}}", end="")
        col_pos += 1

        # EX stage (variable cycles)
        for _ in range(s.clkcyc):
            print(f"{'EX':^{COL}}", end="")
            col_pos += 1

        # WB stage (1 cycle)
        print(f"{'WB':^{COL}}", end="")

        print()  # newline

    print(f"\nPipelined execution completed in {pipelined_clk_cycs} clock cycles.")