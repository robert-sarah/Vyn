; ModuleID = "vyn_module"
target triple = "unknown-unknown-unknown"
target datalayout = ""

declare void @"vyn_io_print_f32"(float %".1")

declare void @"vyn_io_println_str"(i8* %".1")

declare void @"vyn_sys_sleep_ms"(i32 %".1")

declare void @"vyn_profile_begin"(i8* %".1")

declare void @"vyn_profile_end"(i8* %".1", double %".2")

define internal float @"process_data"([500 x float] %".1")
{
entry:
  %".3" = getelementptr inbounds [13 x i8], [13 x i8]* @"str.0", i32 0, i32 0
  call void @"vyn_profile_begin"(i8* %".3")
  %"input" = alloca [500 x float]
  store [500 x float] %".1", [500 x float]* %"input"
  %"sum" = alloca float
  store float              0x0, float* %"sum"
  br label %"loop_cond"
loop_cond:
  %"_loop_i" = alloca i32
  store i32 0, i32* %"_loop_i"
  %".9" = load i32, i32* %"_loop_i"
  %".10" = icmp slt i32 %".9", 500
  br i1 %".10", label %"loop_body", label %"loop_exit"
loop_body:
  %".12" = load i32, i32* %"_loop_i"
  %".13" = getelementptr [500 x float], [500 x float]* %"input", i32 0, i32 %".12"
  %"val" = alloca float
  %".14" = load float, float* %".13"
  store float %".14", float* %"val"
  %".16" = load float, float* %"sum"
  %".17" = load float, float* %"val"
  %".18" = fmul float %".17", 0x4000000000000000
  %".19" = fadd float %".16", %".18"
  store float %".19", float* %"sum"
  %".21" = add i32 %".9", 1
  store i32 %".21", i32* %"_loop_i"
  br label %"loop_cond"
loop_exit:
  %".24" = load float, float* %"sum"
  ret float %".24"
  %".26" = getelementptr inbounds [13 x i8], [13 x i8]* @"str.1", i32 0, i32 0
profile_end:
  call void @"vyn_profile_end"(i8* %".26", double              0x0)
}

define external i32 @"main"()
{
entry:
  %".2" = alloca [500 x float]
  %".3" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 0
  store float 0x3ff0000000000000, float* %".3"
  %".5" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 1
  store float 0x3ff0000000000000, float* %".5"
  %".7" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 2
  store float 0x3ff0000000000000, float* %".7"
  %".9" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 3
  store float 0x3ff0000000000000, float* %".9"
  %".11" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 4
  store float 0x3ff0000000000000, float* %".11"
  %".13" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 5
  store float 0x3ff0000000000000, float* %".13"
  %".15" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 6
  store float 0x3ff0000000000000, float* %".15"
  %".17" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 7
  store float 0x3ff0000000000000, float* %".17"
  %".19" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 8
  store float 0x3ff0000000000000, float* %".19"
  %".21" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 9
  store float 0x3ff0000000000000, float* %".21"
  %".23" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 10
  store float 0x3ff0000000000000, float* %".23"
  %".25" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 11
  store float 0x3ff0000000000000, float* %".25"
  %".27" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 12
  store float 0x3ff0000000000000, float* %".27"
  %".29" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 13
  store float 0x3ff0000000000000, float* %".29"
  %".31" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 14
  store float 0x3ff0000000000000, float* %".31"
  %".33" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 15
  store float 0x3ff0000000000000, float* %".33"
  %".35" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 16
  store float 0x3ff0000000000000, float* %".35"
  %".37" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 17
  store float 0x3ff0000000000000, float* %".37"
  %".39" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 18
  store float 0x3ff0000000000000, float* %".39"
  %".41" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 19
  store float 0x3ff0000000000000, float* %".41"
  %".43" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 20
  store float 0x3ff0000000000000, float* %".43"
  %".45" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 21
  store float 0x3ff0000000000000, float* %".45"
  %".47" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 22
  store float 0x3ff0000000000000, float* %".47"
  %".49" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 23
  store float 0x3ff0000000000000, float* %".49"
  %".51" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 24
  store float 0x3ff0000000000000, float* %".51"
  %".53" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 25
  store float 0x3ff0000000000000, float* %".53"
  %".55" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 26
  store float 0x3ff0000000000000, float* %".55"
  %".57" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 27
  store float 0x3ff0000000000000, float* %".57"
  %".59" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 28
  store float 0x3ff0000000000000, float* %".59"
  %".61" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 29
  store float 0x3ff0000000000000, float* %".61"
  %".63" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 30
  store float 0x3ff0000000000000, float* %".63"
  %".65" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 31
  store float 0x3ff0000000000000, float* %".65"
  %".67" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 32
  store float 0x3ff0000000000000, float* %".67"
  %".69" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 33
  store float 0x3ff0000000000000, float* %".69"
  %".71" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 34
  store float 0x3ff0000000000000, float* %".71"
  %".73" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 35
  store float 0x3ff0000000000000, float* %".73"
  %".75" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 36
  store float 0x3ff0000000000000, float* %".75"
  %".77" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 37
  store float 0x3ff0000000000000, float* %".77"
  %".79" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 38
  store float 0x3ff0000000000000, float* %".79"
  %".81" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 39
  store float 0x3ff0000000000000, float* %".81"
  %".83" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 40
  store float 0x3ff0000000000000, float* %".83"
  %".85" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 41
  store float 0x3ff0000000000000, float* %".85"
  %".87" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 42
  store float 0x3ff0000000000000, float* %".87"
  %".89" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 43
  store float 0x3ff0000000000000, float* %".89"
  %".91" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 44
  store float 0x3ff0000000000000, float* %".91"
  %".93" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 45
  store float 0x3ff0000000000000, float* %".93"
  %".95" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 46
  store float 0x3ff0000000000000, float* %".95"
  %".97" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 47
  store float 0x3ff0000000000000, float* %".97"
  %".99" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 48
  store float 0x3ff0000000000000, float* %".99"
  %".101" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 49
  store float 0x3ff0000000000000, float* %".101"
  %".103" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 50
  store float 0x3ff0000000000000, float* %".103"
  %".105" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 51
  store float 0x3ff0000000000000, float* %".105"
  %".107" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 52
  store float 0x3ff0000000000000, float* %".107"
  %".109" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 53
  store float 0x3ff0000000000000, float* %".109"
  %".111" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 54
  store float 0x3ff0000000000000, float* %".111"
  %".113" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 55
  store float 0x3ff0000000000000, float* %".113"
  %".115" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 56
  store float 0x3ff0000000000000, float* %".115"
  %".117" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 57
  store float 0x3ff0000000000000, float* %".117"
  %".119" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 58
  store float 0x3ff0000000000000, float* %".119"
  %".121" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 59
  store float 0x3ff0000000000000, float* %".121"
  %".123" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 60
  store float 0x3ff0000000000000, float* %".123"
  %".125" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 61
  store float 0x3ff0000000000000, float* %".125"
  %".127" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 62
  store float 0x3ff0000000000000, float* %".127"
  %".129" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 63
  store float 0x3ff0000000000000, float* %".129"
  %".131" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 64
  store float 0x3ff0000000000000, float* %".131"
  %".133" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 65
  store float 0x3ff0000000000000, float* %".133"
  %".135" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 66
  store float 0x3ff0000000000000, float* %".135"
  %".137" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 67
  store float 0x3ff0000000000000, float* %".137"
  %".139" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 68
  store float 0x3ff0000000000000, float* %".139"
  %".141" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 69
  store float 0x3ff0000000000000, float* %".141"
  %".143" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 70
  store float 0x3ff0000000000000, float* %".143"
  %".145" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 71
  store float 0x3ff0000000000000, float* %".145"
  %".147" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 72
  store float 0x3ff0000000000000, float* %".147"
  %".149" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 73
  store float 0x3ff0000000000000, float* %".149"
  %".151" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 74
  store float 0x3ff0000000000000, float* %".151"
  %".153" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 75
  store float 0x3ff0000000000000, float* %".153"
  %".155" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 76
  store float 0x3ff0000000000000, float* %".155"
  %".157" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 77
  store float 0x3ff0000000000000, float* %".157"
  %".159" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 78
  store float 0x3ff0000000000000, float* %".159"
  %".161" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 79
  store float 0x3ff0000000000000, float* %".161"
  %".163" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 80
  store float 0x3ff0000000000000, float* %".163"
  %".165" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 81
  store float 0x3ff0000000000000, float* %".165"
  %".167" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 82
  store float 0x3ff0000000000000, float* %".167"
  %".169" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 83
  store float 0x3ff0000000000000, float* %".169"
  %".171" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 84
  store float 0x3ff0000000000000, float* %".171"
  %".173" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 85
  store float 0x3ff0000000000000, float* %".173"
  %".175" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 86
  store float 0x3ff0000000000000, float* %".175"
  %".177" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 87
  store float 0x3ff0000000000000, float* %".177"
  %".179" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 88
  store float 0x3ff0000000000000, float* %".179"
  %".181" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 89
  store float 0x3ff0000000000000, float* %".181"
  %".183" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 90
  store float 0x3ff0000000000000, float* %".183"
  %".185" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 91
  store float 0x3ff0000000000000, float* %".185"
  %".187" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 92
  store float 0x3ff0000000000000, float* %".187"
  %".189" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 93
  store float 0x3ff0000000000000, float* %".189"
  %".191" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 94
  store float 0x3ff0000000000000, float* %".191"
  %".193" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 95
  store float 0x3ff0000000000000, float* %".193"
  %".195" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 96
  store float 0x3ff0000000000000, float* %".195"
  %".197" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 97
  store float 0x3ff0000000000000, float* %".197"
  %".199" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 98
  store float 0x3ff0000000000000, float* %".199"
  %".201" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 99
  store float 0x3ff0000000000000, float* %".201"
  %".203" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 100
  store float 0x3ff0000000000000, float* %".203"
  %".205" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 101
  store float 0x3ff0000000000000, float* %".205"
  %".207" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 102
  store float 0x3ff0000000000000, float* %".207"
  %".209" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 103
  store float 0x3ff0000000000000, float* %".209"
  %".211" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 104
  store float 0x3ff0000000000000, float* %".211"
  %".213" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 105
  store float 0x3ff0000000000000, float* %".213"
  %".215" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 106
  store float 0x3ff0000000000000, float* %".215"
  %".217" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 107
  store float 0x3ff0000000000000, float* %".217"
  %".219" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 108
  store float 0x3ff0000000000000, float* %".219"
  %".221" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 109
  store float 0x3ff0000000000000, float* %".221"
  %".223" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 110
  store float 0x3ff0000000000000, float* %".223"
  %".225" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 111
  store float 0x3ff0000000000000, float* %".225"
  %".227" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 112
  store float 0x3ff0000000000000, float* %".227"
  %".229" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 113
  store float 0x3ff0000000000000, float* %".229"
  %".231" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 114
  store float 0x3ff0000000000000, float* %".231"
  %".233" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 115
  store float 0x3ff0000000000000, float* %".233"
  %".235" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 116
  store float 0x3ff0000000000000, float* %".235"
  %".237" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 117
  store float 0x3ff0000000000000, float* %".237"
  %".239" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 118
  store float 0x3ff0000000000000, float* %".239"
  %".241" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 119
  store float 0x3ff0000000000000, float* %".241"
  %".243" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 120
  store float 0x3ff0000000000000, float* %".243"
  %".245" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 121
  store float 0x3ff0000000000000, float* %".245"
  %".247" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 122
  store float 0x3ff0000000000000, float* %".247"
  %".249" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 123
  store float 0x3ff0000000000000, float* %".249"
  %".251" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 124
  store float 0x3ff0000000000000, float* %".251"
  %".253" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 125
  store float 0x3ff0000000000000, float* %".253"
  %".255" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 126
  store float 0x3ff0000000000000, float* %".255"
  %".257" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 127
  store float 0x3ff0000000000000, float* %".257"
  %".259" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 128
  store float 0x3ff0000000000000, float* %".259"
  %".261" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 129
  store float 0x3ff0000000000000, float* %".261"
  %".263" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 130
  store float 0x3ff0000000000000, float* %".263"
  %".265" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 131
  store float 0x3ff0000000000000, float* %".265"
  %".267" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 132
  store float 0x3ff0000000000000, float* %".267"
  %".269" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 133
  store float 0x3ff0000000000000, float* %".269"
  %".271" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 134
  store float 0x3ff0000000000000, float* %".271"
  %".273" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 135
  store float 0x3ff0000000000000, float* %".273"
  %".275" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 136
  store float 0x3ff0000000000000, float* %".275"
  %".277" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 137
  store float 0x3ff0000000000000, float* %".277"
  %".279" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 138
  store float 0x3ff0000000000000, float* %".279"
  %".281" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 139
  store float 0x3ff0000000000000, float* %".281"
  %".283" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 140
  store float 0x3ff0000000000000, float* %".283"
  %".285" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 141
  store float 0x3ff0000000000000, float* %".285"
  %".287" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 142
  store float 0x3ff0000000000000, float* %".287"
  %".289" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 143
  store float 0x3ff0000000000000, float* %".289"
  %".291" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 144
  store float 0x3ff0000000000000, float* %".291"
  %".293" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 145
  store float 0x3ff0000000000000, float* %".293"
  %".295" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 146
  store float 0x3ff0000000000000, float* %".295"
  %".297" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 147
  store float 0x3ff0000000000000, float* %".297"
  %".299" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 148
  store float 0x3ff0000000000000, float* %".299"
  %".301" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 149
  store float 0x3ff0000000000000, float* %".301"
  %".303" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 150
  store float 0x3ff0000000000000, float* %".303"
  %".305" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 151
  store float 0x3ff0000000000000, float* %".305"
  %".307" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 152
  store float 0x3ff0000000000000, float* %".307"
  %".309" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 153
  store float 0x3ff0000000000000, float* %".309"
  %".311" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 154
  store float 0x3ff0000000000000, float* %".311"
  %".313" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 155
  store float 0x3ff0000000000000, float* %".313"
  %".315" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 156
  store float 0x3ff0000000000000, float* %".315"
  %".317" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 157
  store float 0x3ff0000000000000, float* %".317"
  %".319" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 158
  store float 0x3ff0000000000000, float* %".319"
  %".321" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 159
  store float 0x3ff0000000000000, float* %".321"
  %".323" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 160
  store float 0x3ff0000000000000, float* %".323"
  %".325" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 161
  store float 0x3ff0000000000000, float* %".325"
  %".327" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 162
  store float 0x3ff0000000000000, float* %".327"
  %".329" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 163
  store float 0x3ff0000000000000, float* %".329"
  %".331" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 164
  store float 0x3ff0000000000000, float* %".331"
  %".333" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 165
  store float 0x3ff0000000000000, float* %".333"
  %".335" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 166
  store float 0x3ff0000000000000, float* %".335"
  %".337" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 167
  store float 0x3ff0000000000000, float* %".337"
  %".339" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 168
  store float 0x3ff0000000000000, float* %".339"
  %".341" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 169
  store float 0x3ff0000000000000, float* %".341"
  %".343" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 170
  store float 0x3ff0000000000000, float* %".343"
  %".345" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 171
  store float 0x3ff0000000000000, float* %".345"
  %".347" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 172
  store float 0x3ff0000000000000, float* %".347"
  %".349" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 173
  store float 0x3ff0000000000000, float* %".349"
  %".351" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 174
  store float 0x3ff0000000000000, float* %".351"
  %".353" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 175
  store float 0x3ff0000000000000, float* %".353"
  %".355" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 176
  store float 0x3ff0000000000000, float* %".355"
  %".357" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 177
  store float 0x3ff0000000000000, float* %".357"
  %".359" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 178
  store float 0x3ff0000000000000, float* %".359"
  %".361" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 179
  store float 0x3ff0000000000000, float* %".361"
  %".363" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 180
  store float 0x3ff0000000000000, float* %".363"
  %".365" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 181
  store float 0x3ff0000000000000, float* %".365"
  %".367" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 182
  store float 0x3ff0000000000000, float* %".367"
  %".369" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 183
  store float 0x3ff0000000000000, float* %".369"
  %".371" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 184
  store float 0x3ff0000000000000, float* %".371"
  %".373" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 185
  store float 0x3ff0000000000000, float* %".373"
  %".375" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 186
  store float 0x3ff0000000000000, float* %".375"
  %".377" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 187
  store float 0x3ff0000000000000, float* %".377"
  %".379" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 188
  store float 0x3ff0000000000000, float* %".379"
  %".381" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 189
  store float 0x3ff0000000000000, float* %".381"
  %".383" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 190
  store float 0x3ff0000000000000, float* %".383"
  %".385" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 191
  store float 0x3ff0000000000000, float* %".385"
  %".387" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 192
  store float 0x3ff0000000000000, float* %".387"
  %".389" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 193
  store float 0x3ff0000000000000, float* %".389"
  %".391" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 194
  store float 0x3ff0000000000000, float* %".391"
  %".393" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 195
  store float 0x3ff0000000000000, float* %".393"
  %".395" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 196
  store float 0x3ff0000000000000, float* %".395"
  %".397" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 197
  store float 0x3ff0000000000000, float* %".397"
  %".399" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 198
  store float 0x3ff0000000000000, float* %".399"
  %".401" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 199
  store float 0x3ff0000000000000, float* %".401"
  %".403" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 200
  store float 0x3ff0000000000000, float* %".403"
  %".405" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 201
  store float 0x3ff0000000000000, float* %".405"
  %".407" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 202
  store float 0x3ff0000000000000, float* %".407"
  %".409" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 203
  store float 0x3ff0000000000000, float* %".409"
  %".411" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 204
  store float 0x3ff0000000000000, float* %".411"
  %".413" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 205
  store float 0x3ff0000000000000, float* %".413"
  %".415" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 206
  store float 0x3ff0000000000000, float* %".415"
  %".417" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 207
  store float 0x3ff0000000000000, float* %".417"
  %".419" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 208
  store float 0x3ff0000000000000, float* %".419"
  %".421" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 209
  store float 0x3ff0000000000000, float* %".421"
  %".423" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 210
  store float 0x3ff0000000000000, float* %".423"
  %".425" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 211
  store float 0x3ff0000000000000, float* %".425"
  %".427" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 212
  store float 0x3ff0000000000000, float* %".427"
  %".429" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 213
  store float 0x3ff0000000000000, float* %".429"
  %".431" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 214
  store float 0x3ff0000000000000, float* %".431"
  %".433" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 215
  store float 0x3ff0000000000000, float* %".433"
  %".435" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 216
  store float 0x3ff0000000000000, float* %".435"
  %".437" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 217
  store float 0x3ff0000000000000, float* %".437"
  %".439" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 218
  store float 0x3ff0000000000000, float* %".439"
  %".441" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 219
  store float 0x3ff0000000000000, float* %".441"
  %".443" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 220
  store float 0x3ff0000000000000, float* %".443"
  %".445" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 221
  store float 0x3ff0000000000000, float* %".445"
  %".447" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 222
  store float 0x3ff0000000000000, float* %".447"
  %".449" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 223
  store float 0x3ff0000000000000, float* %".449"
  %".451" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 224
  store float 0x3ff0000000000000, float* %".451"
  %".453" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 225
  store float 0x3ff0000000000000, float* %".453"
  %".455" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 226
  store float 0x3ff0000000000000, float* %".455"
  %".457" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 227
  store float 0x3ff0000000000000, float* %".457"
  %".459" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 228
  store float 0x3ff0000000000000, float* %".459"
  %".461" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 229
  store float 0x3ff0000000000000, float* %".461"
  %".463" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 230
  store float 0x3ff0000000000000, float* %".463"
  %".465" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 231
  store float 0x3ff0000000000000, float* %".465"
  %".467" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 232
  store float 0x3ff0000000000000, float* %".467"
  %".469" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 233
  store float 0x3ff0000000000000, float* %".469"
  %".471" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 234
  store float 0x3ff0000000000000, float* %".471"
  %".473" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 235
  store float 0x3ff0000000000000, float* %".473"
  %".475" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 236
  store float 0x3ff0000000000000, float* %".475"
  %".477" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 237
  store float 0x3ff0000000000000, float* %".477"
  %".479" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 238
  store float 0x3ff0000000000000, float* %".479"
  %".481" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 239
  store float 0x3ff0000000000000, float* %".481"
  %".483" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 240
  store float 0x3ff0000000000000, float* %".483"
  %".485" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 241
  store float 0x3ff0000000000000, float* %".485"
  %".487" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 242
  store float 0x3ff0000000000000, float* %".487"
  %".489" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 243
  store float 0x3ff0000000000000, float* %".489"
  %".491" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 244
  store float 0x3ff0000000000000, float* %".491"
  %".493" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 245
  store float 0x3ff0000000000000, float* %".493"
  %".495" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 246
  store float 0x3ff0000000000000, float* %".495"
  %".497" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 247
  store float 0x3ff0000000000000, float* %".497"
  %".499" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 248
  store float 0x3ff0000000000000, float* %".499"
  %".501" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 249
  store float 0x3ff0000000000000, float* %".501"
  %".503" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 250
  store float 0x3ff0000000000000, float* %".503"
  %".505" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 251
  store float 0x3ff0000000000000, float* %".505"
  %".507" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 252
  store float 0x3ff0000000000000, float* %".507"
  %".509" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 253
  store float 0x3ff0000000000000, float* %".509"
  %".511" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 254
  store float 0x3ff0000000000000, float* %".511"
  %".513" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 255
  store float 0x3ff0000000000000, float* %".513"
  %".515" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 256
  store float 0x3ff0000000000000, float* %".515"
  %".517" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 257
  store float 0x3ff0000000000000, float* %".517"
  %".519" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 258
  store float 0x3ff0000000000000, float* %".519"
  %".521" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 259
  store float 0x3ff0000000000000, float* %".521"
  %".523" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 260
  store float 0x3ff0000000000000, float* %".523"
  %".525" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 261
  store float 0x3ff0000000000000, float* %".525"
  %".527" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 262
  store float 0x3ff0000000000000, float* %".527"
  %".529" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 263
  store float 0x3ff0000000000000, float* %".529"
  %".531" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 264
  store float 0x3ff0000000000000, float* %".531"
  %".533" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 265
  store float 0x3ff0000000000000, float* %".533"
  %".535" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 266
  store float 0x3ff0000000000000, float* %".535"
  %".537" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 267
  store float 0x3ff0000000000000, float* %".537"
  %".539" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 268
  store float 0x3ff0000000000000, float* %".539"
  %".541" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 269
  store float 0x3ff0000000000000, float* %".541"
  %".543" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 270
  store float 0x3ff0000000000000, float* %".543"
  %".545" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 271
  store float 0x3ff0000000000000, float* %".545"
  %".547" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 272
  store float 0x3ff0000000000000, float* %".547"
  %".549" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 273
  store float 0x3ff0000000000000, float* %".549"
  %".551" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 274
  store float 0x3ff0000000000000, float* %".551"
  %".553" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 275
  store float 0x3ff0000000000000, float* %".553"
  %".555" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 276
  store float 0x3ff0000000000000, float* %".555"
  %".557" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 277
  store float 0x3ff0000000000000, float* %".557"
  %".559" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 278
  store float 0x3ff0000000000000, float* %".559"
  %".561" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 279
  store float 0x3ff0000000000000, float* %".561"
  %".563" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 280
  store float 0x3ff0000000000000, float* %".563"
  %".565" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 281
  store float 0x3ff0000000000000, float* %".565"
  %".567" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 282
  store float 0x3ff0000000000000, float* %".567"
  %".569" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 283
  store float 0x3ff0000000000000, float* %".569"
  %".571" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 284
  store float 0x3ff0000000000000, float* %".571"
  %".573" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 285
  store float 0x3ff0000000000000, float* %".573"
  %".575" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 286
  store float 0x3ff0000000000000, float* %".575"
  %".577" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 287
  store float 0x3ff0000000000000, float* %".577"
  %".579" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 288
  store float 0x3ff0000000000000, float* %".579"
  %".581" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 289
  store float 0x3ff0000000000000, float* %".581"
  %".583" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 290
  store float 0x3ff0000000000000, float* %".583"
  %".585" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 291
  store float 0x3ff0000000000000, float* %".585"
  %".587" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 292
  store float 0x3ff0000000000000, float* %".587"
  %".589" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 293
  store float 0x3ff0000000000000, float* %".589"
  %".591" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 294
  store float 0x3ff0000000000000, float* %".591"
  %".593" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 295
  store float 0x3ff0000000000000, float* %".593"
  %".595" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 296
  store float 0x3ff0000000000000, float* %".595"
  %".597" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 297
  store float 0x3ff0000000000000, float* %".597"
  %".599" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 298
  store float 0x3ff0000000000000, float* %".599"
  %".601" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 299
  store float 0x3ff0000000000000, float* %".601"
  %".603" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 300
  store float 0x3ff0000000000000, float* %".603"
  %".605" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 301
  store float 0x3ff0000000000000, float* %".605"
  %".607" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 302
  store float 0x3ff0000000000000, float* %".607"
  %".609" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 303
  store float 0x3ff0000000000000, float* %".609"
  %".611" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 304
  store float 0x3ff0000000000000, float* %".611"
  %".613" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 305
  store float 0x3ff0000000000000, float* %".613"
  %".615" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 306
  store float 0x3ff0000000000000, float* %".615"
  %".617" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 307
  store float 0x3ff0000000000000, float* %".617"
  %".619" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 308
  store float 0x3ff0000000000000, float* %".619"
  %".621" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 309
  store float 0x3ff0000000000000, float* %".621"
  %".623" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 310
  store float 0x3ff0000000000000, float* %".623"
  %".625" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 311
  store float 0x3ff0000000000000, float* %".625"
  %".627" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 312
  store float 0x3ff0000000000000, float* %".627"
  %".629" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 313
  store float 0x3ff0000000000000, float* %".629"
  %".631" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 314
  store float 0x3ff0000000000000, float* %".631"
  %".633" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 315
  store float 0x3ff0000000000000, float* %".633"
  %".635" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 316
  store float 0x3ff0000000000000, float* %".635"
  %".637" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 317
  store float 0x3ff0000000000000, float* %".637"
  %".639" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 318
  store float 0x3ff0000000000000, float* %".639"
  %".641" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 319
  store float 0x3ff0000000000000, float* %".641"
  %".643" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 320
  store float 0x3ff0000000000000, float* %".643"
  %".645" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 321
  store float 0x3ff0000000000000, float* %".645"
  %".647" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 322
  store float 0x3ff0000000000000, float* %".647"
  %".649" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 323
  store float 0x3ff0000000000000, float* %".649"
  %".651" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 324
  store float 0x3ff0000000000000, float* %".651"
  %".653" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 325
  store float 0x3ff0000000000000, float* %".653"
  %".655" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 326
  store float 0x3ff0000000000000, float* %".655"
  %".657" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 327
  store float 0x3ff0000000000000, float* %".657"
  %".659" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 328
  store float 0x3ff0000000000000, float* %".659"
  %".661" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 329
  store float 0x3ff0000000000000, float* %".661"
  %".663" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 330
  store float 0x3ff0000000000000, float* %".663"
  %".665" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 331
  store float 0x3ff0000000000000, float* %".665"
  %".667" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 332
  store float 0x3ff0000000000000, float* %".667"
  %".669" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 333
  store float 0x3ff0000000000000, float* %".669"
  %".671" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 334
  store float 0x3ff0000000000000, float* %".671"
  %".673" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 335
  store float 0x3ff0000000000000, float* %".673"
  %".675" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 336
  store float 0x3ff0000000000000, float* %".675"
  %".677" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 337
  store float 0x3ff0000000000000, float* %".677"
  %".679" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 338
  store float 0x3ff0000000000000, float* %".679"
  %".681" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 339
  store float 0x3ff0000000000000, float* %".681"
  %".683" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 340
  store float 0x3ff0000000000000, float* %".683"
  %".685" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 341
  store float 0x3ff0000000000000, float* %".685"
  %".687" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 342
  store float 0x3ff0000000000000, float* %".687"
  %".689" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 343
  store float 0x3ff0000000000000, float* %".689"
  %".691" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 344
  store float 0x3ff0000000000000, float* %".691"
  %".693" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 345
  store float 0x3ff0000000000000, float* %".693"
  %".695" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 346
  store float 0x3ff0000000000000, float* %".695"
  %".697" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 347
  store float 0x3ff0000000000000, float* %".697"
  %".699" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 348
  store float 0x3ff0000000000000, float* %".699"
  %".701" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 349
  store float 0x3ff0000000000000, float* %".701"
  %".703" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 350
  store float 0x3ff0000000000000, float* %".703"
  %".705" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 351
  store float 0x3ff0000000000000, float* %".705"
  %".707" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 352
  store float 0x3ff0000000000000, float* %".707"
  %".709" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 353
  store float 0x3ff0000000000000, float* %".709"
  %".711" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 354
  store float 0x3ff0000000000000, float* %".711"
  %".713" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 355
  store float 0x3ff0000000000000, float* %".713"
  %".715" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 356
  store float 0x3ff0000000000000, float* %".715"
  %".717" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 357
  store float 0x3ff0000000000000, float* %".717"
  %".719" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 358
  store float 0x3ff0000000000000, float* %".719"
  %".721" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 359
  store float 0x3ff0000000000000, float* %".721"
  %".723" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 360
  store float 0x3ff0000000000000, float* %".723"
  %".725" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 361
  store float 0x3ff0000000000000, float* %".725"
  %".727" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 362
  store float 0x3ff0000000000000, float* %".727"
  %".729" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 363
  store float 0x3ff0000000000000, float* %".729"
  %".731" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 364
  store float 0x3ff0000000000000, float* %".731"
  %".733" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 365
  store float 0x3ff0000000000000, float* %".733"
  %".735" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 366
  store float 0x3ff0000000000000, float* %".735"
  %".737" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 367
  store float 0x3ff0000000000000, float* %".737"
  %".739" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 368
  store float 0x3ff0000000000000, float* %".739"
  %".741" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 369
  store float 0x3ff0000000000000, float* %".741"
  %".743" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 370
  store float 0x3ff0000000000000, float* %".743"
  %".745" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 371
  store float 0x3ff0000000000000, float* %".745"
  %".747" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 372
  store float 0x3ff0000000000000, float* %".747"
  %".749" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 373
  store float 0x3ff0000000000000, float* %".749"
  %".751" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 374
  store float 0x3ff0000000000000, float* %".751"
  %".753" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 375
  store float 0x3ff0000000000000, float* %".753"
  %".755" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 376
  store float 0x3ff0000000000000, float* %".755"
  %".757" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 377
  store float 0x3ff0000000000000, float* %".757"
  %".759" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 378
  store float 0x3ff0000000000000, float* %".759"
  %".761" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 379
  store float 0x3ff0000000000000, float* %".761"
  %".763" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 380
  store float 0x3ff0000000000000, float* %".763"
  %".765" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 381
  store float 0x3ff0000000000000, float* %".765"
  %".767" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 382
  store float 0x3ff0000000000000, float* %".767"
  %".769" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 383
  store float 0x3ff0000000000000, float* %".769"
  %".771" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 384
  store float 0x3ff0000000000000, float* %".771"
  %".773" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 385
  store float 0x3ff0000000000000, float* %".773"
  %".775" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 386
  store float 0x3ff0000000000000, float* %".775"
  %".777" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 387
  store float 0x3ff0000000000000, float* %".777"
  %".779" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 388
  store float 0x3ff0000000000000, float* %".779"
  %".781" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 389
  store float 0x3ff0000000000000, float* %".781"
  %".783" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 390
  store float 0x3ff0000000000000, float* %".783"
  %".785" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 391
  store float 0x3ff0000000000000, float* %".785"
  %".787" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 392
  store float 0x3ff0000000000000, float* %".787"
  %".789" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 393
  store float 0x3ff0000000000000, float* %".789"
  %".791" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 394
  store float 0x3ff0000000000000, float* %".791"
  %".793" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 395
  store float 0x3ff0000000000000, float* %".793"
  %".795" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 396
  store float 0x3ff0000000000000, float* %".795"
  %".797" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 397
  store float 0x3ff0000000000000, float* %".797"
  %".799" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 398
  store float 0x3ff0000000000000, float* %".799"
  %".801" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 399
  store float 0x3ff0000000000000, float* %".801"
  %".803" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 400
  store float 0x3ff0000000000000, float* %".803"
  %".805" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 401
  store float 0x3ff0000000000000, float* %".805"
  %".807" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 402
  store float 0x3ff0000000000000, float* %".807"
  %".809" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 403
  store float 0x3ff0000000000000, float* %".809"
  %".811" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 404
  store float 0x3ff0000000000000, float* %".811"
  %".813" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 405
  store float 0x3ff0000000000000, float* %".813"
  %".815" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 406
  store float 0x3ff0000000000000, float* %".815"
  %".817" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 407
  store float 0x3ff0000000000000, float* %".817"
  %".819" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 408
  store float 0x3ff0000000000000, float* %".819"
  %".821" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 409
  store float 0x3ff0000000000000, float* %".821"
  %".823" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 410
  store float 0x3ff0000000000000, float* %".823"
  %".825" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 411
  store float 0x3ff0000000000000, float* %".825"
  %".827" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 412
  store float 0x3ff0000000000000, float* %".827"
  %".829" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 413
  store float 0x3ff0000000000000, float* %".829"
  %".831" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 414
  store float 0x3ff0000000000000, float* %".831"
  %".833" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 415
  store float 0x3ff0000000000000, float* %".833"
  %".835" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 416
  store float 0x3ff0000000000000, float* %".835"
  %".837" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 417
  store float 0x3ff0000000000000, float* %".837"
  %".839" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 418
  store float 0x3ff0000000000000, float* %".839"
  %".841" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 419
  store float 0x3ff0000000000000, float* %".841"
  %".843" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 420
  store float 0x3ff0000000000000, float* %".843"
  %".845" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 421
  store float 0x3ff0000000000000, float* %".845"
  %".847" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 422
  store float 0x3ff0000000000000, float* %".847"
  %".849" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 423
  store float 0x3ff0000000000000, float* %".849"
  %".851" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 424
  store float 0x3ff0000000000000, float* %".851"
  %".853" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 425
  store float 0x3ff0000000000000, float* %".853"
  %".855" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 426
  store float 0x3ff0000000000000, float* %".855"
  %".857" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 427
  store float 0x3ff0000000000000, float* %".857"
  %".859" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 428
  store float 0x3ff0000000000000, float* %".859"
  %".861" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 429
  store float 0x3ff0000000000000, float* %".861"
  %".863" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 430
  store float 0x3ff0000000000000, float* %".863"
  %".865" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 431
  store float 0x3ff0000000000000, float* %".865"
  %".867" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 432
  store float 0x3ff0000000000000, float* %".867"
  %".869" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 433
  store float 0x3ff0000000000000, float* %".869"
  %".871" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 434
  store float 0x3ff0000000000000, float* %".871"
  %".873" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 435
  store float 0x3ff0000000000000, float* %".873"
  %".875" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 436
  store float 0x3ff0000000000000, float* %".875"
  %".877" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 437
  store float 0x3ff0000000000000, float* %".877"
  %".879" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 438
  store float 0x3ff0000000000000, float* %".879"
  %".881" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 439
  store float 0x3ff0000000000000, float* %".881"
  %".883" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 440
  store float 0x3ff0000000000000, float* %".883"
  %".885" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 441
  store float 0x3ff0000000000000, float* %".885"
  %".887" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 442
  store float 0x3ff0000000000000, float* %".887"
  %".889" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 443
  store float 0x3ff0000000000000, float* %".889"
  %".891" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 444
  store float 0x3ff0000000000000, float* %".891"
  %".893" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 445
  store float 0x3ff0000000000000, float* %".893"
  %".895" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 446
  store float 0x3ff0000000000000, float* %".895"
  %".897" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 447
  store float 0x3ff0000000000000, float* %".897"
  %".899" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 448
  store float 0x3ff0000000000000, float* %".899"
  %".901" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 449
  store float 0x3ff0000000000000, float* %".901"
  %".903" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 450
  store float 0x3ff0000000000000, float* %".903"
  %".905" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 451
  store float 0x3ff0000000000000, float* %".905"
  %".907" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 452
  store float 0x3ff0000000000000, float* %".907"
  %".909" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 453
  store float 0x3ff0000000000000, float* %".909"
  %".911" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 454
  store float 0x3ff0000000000000, float* %".911"
  %".913" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 455
  store float 0x3ff0000000000000, float* %".913"
  %".915" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 456
  store float 0x3ff0000000000000, float* %".915"
  %".917" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 457
  store float 0x3ff0000000000000, float* %".917"
  %".919" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 458
  store float 0x3ff0000000000000, float* %".919"
  %".921" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 459
  store float 0x3ff0000000000000, float* %".921"
  %".923" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 460
  store float 0x3ff0000000000000, float* %".923"
  %".925" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 461
  store float 0x3ff0000000000000, float* %".925"
  %".927" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 462
  store float 0x3ff0000000000000, float* %".927"
  %".929" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 463
  store float 0x3ff0000000000000, float* %".929"
  %".931" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 464
  store float 0x3ff0000000000000, float* %".931"
  %".933" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 465
  store float 0x3ff0000000000000, float* %".933"
  %".935" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 466
  store float 0x3ff0000000000000, float* %".935"
  %".937" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 467
  store float 0x3ff0000000000000, float* %".937"
  %".939" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 468
  store float 0x3ff0000000000000, float* %".939"
  %".941" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 469
  store float 0x3ff0000000000000, float* %".941"
  %".943" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 470
  store float 0x3ff0000000000000, float* %".943"
  %".945" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 471
  store float 0x3ff0000000000000, float* %".945"
  %".947" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 472
  store float 0x3ff0000000000000, float* %".947"
  %".949" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 473
  store float 0x3ff0000000000000, float* %".949"
  %".951" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 474
  store float 0x3ff0000000000000, float* %".951"
  %".953" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 475
  store float 0x3ff0000000000000, float* %".953"
  %".955" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 476
  store float 0x3ff0000000000000, float* %".955"
  %".957" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 477
  store float 0x3ff0000000000000, float* %".957"
  %".959" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 478
  store float 0x3ff0000000000000, float* %".959"
  %".961" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 479
  store float 0x3ff0000000000000, float* %".961"
  %".963" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 480
  store float 0x3ff0000000000000, float* %".963"
  %".965" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 481
  store float 0x3ff0000000000000, float* %".965"
  %".967" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 482
  store float 0x3ff0000000000000, float* %".967"
  %".969" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 483
  store float 0x3ff0000000000000, float* %".969"
  %".971" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 484
  store float 0x3ff0000000000000, float* %".971"
  %".973" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 485
  store float 0x3ff0000000000000, float* %".973"
  %".975" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 486
  store float 0x3ff0000000000000, float* %".975"
  %".977" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 487
  store float 0x3ff0000000000000, float* %".977"
  %".979" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 488
  store float 0x3ff0000000000000, float* %".979"
  %".981" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 489
  store float 0x3ff0000000000000, float* %".981"
  %".983" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 490
  store float 0x3ff0000000000000, float* %".983"
  %".985" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 491
  store float 0x3ff0000000000000, float* %".985"
  %".987" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 492
  store float 0x3ff0000000000000, float* %".987"
  %".989" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 493
  store float 0x3ff0000000000000, float* %".989"
  %".991" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 494
  store float 0x3ff0000000000000, float* %".991"
  %".993" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 495
  store float 0x3ff0000000000000, float* %".993"
  %".995" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 496
  store float 0x3ff0000000000000, float* %".995"
  %".997" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 497
  store float 0x3ff0000000000000, float* %".997"
  %".999" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 498
  store float 0x3ff0000000000000, float* %".999"
  %".1001" = getelementptr [500 x float], [500 x float]* %".2", i32 0, i32 499
  store float 0x3ff0000000000000, float* %".1001"
  %".1003" = alloca [500 x float]
  %".1004" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 0
  store float 0x3ff0000000000000, float* %".1004"
  %".1006" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 1
  store float 0x3ff0000000000000, float* %".1006"
  %".1008" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 2
  store float 0x3ff0000000000000, float* %".1008"
  %".1010" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 3
  store float 0x3ff0000000000000, float* %".1010"
  %".1012" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 4
  store float 0x3ff0000000000000, float* %".1012"
  %".1014" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 5
  store float 0x3ff0000000000000, float* %".1014"
  %".1016" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 6
  store float 0x3ff0000000000000, float* %".1016"
  %".1018" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 7
  store float 0x3ff0000000000000, float* %".1018"
  %".1020" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 8
  store float 0x3ff0000000000000, float* %".1020"
  %".1022" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 9
  store float 0x3ff0000000000000, float* %".1022"
  %".1024" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 10
  store float 0x3ff0000000000000, float* %".1024"
  %".1026" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 11
  store float 0x3ff0000000000000, float* %".1026"
  %".1028" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 12
  store float 0x3ff0000000000000, float* %".1028"
  %".1030" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 13
  store float 0x3ff0000000000000, float* %".1030"
  %".1032" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 14
  store float 0x3ff0000000000000, float* %".1032"
  %".1034" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 15
  store float 0x3ff0000000000000, float* %".1034"
  %".1036" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 16
  store float 0x3ff0000000000000, float* %".1036"
  %".1038" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 17
  store float 0x3ff0000000000000, float* %".1038"
  %".1040" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 18
  store float 0x3ff0000000000000, float* %".1040"
  %".1042" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 19
  store float 0x3ff0000000000000, float* %".1042"
  %".1044" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 20
  store float 0x3ff0000000000000, float* %".1044"
  %".1046" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 21
  store float 0x3ff0000000000000, float* %".1046"
  %".1048" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 22
  store float 0x3ff0000000000000, float* %".1048"
  %".1050" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 23
  store float 0x3ff0000000000000, float* %".1050"
  %".1052" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 24
  store float 0x3ff0000000000000, float* %".1052"
  %".1054" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 25
  store float 0x3ff0000000000000, float* %".1054"
  %".1056" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 26
  store float 0x3ff0000000000000, float* %".1056"
  %".1058" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 27
  store float 0x3ff0000000000000, float* %".1058"
  %".1060" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 28
  store float 0x3ff0000000000000, float* %".1060"
  %".1062" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 29
  store float 0x3ff0000000000000, float* %".1062"
  %".1064" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 30
  store float 0x3ff0000000000000, float* %".1064"
  %".1066" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 31
  store float 0x3ff0000000000000, float* %".1066"
  %".1068" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 32
  store float 0x3ff0000000000000, float* %".1068"
  %".1070" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 33
  store float 0x3ff0000000000000, float* %".1070"
  %".1072" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 34
  store float 0x3ff0000000000000, float* %".1072"
  %".1074" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 35
  store float 0x3ff0000000000000, float* %".1074"
  %".1076" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 36
  store float 0x3ff0000000000000, float* %".1076"
  %".1078" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 37
  store float 0x3ff0000000000000, float* %".1078"
  %".1080" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 38
  store float 0x3ff0000000000000, float* %".1080"
  %".1082" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 39
  store float 0x3ff0000000000000, float* %".1082"
  %".1084" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 40
  store float 0x3ff0000000000000, float* %".1084"
  %".1086" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 41
  store float 0x3ff0000000000000, float* %".1086"
  %".1088" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 42
  store float 0x3ff0000000000000, float* %".1088"
  %".1090" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 43
  store float 0x3ff0000000000000, float* %".1090"
  %".1092" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 44
  store float 0x3ff0000000000000, float* %".1092"
  %".1094" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 45
  store float 0x3ff0000000000000, float* %".1094"
  %".1096" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 46
  store float 0x3ff0000000000000, float* %".1096"
  %".1098" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 47
  store float 0x3ff0000000000000, float* %".1098"
  %".1100" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 48
  store float 0x3ff0000000000000, float* %".1100"
  %".1102" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 49
  store float 0x3ff0000000000000, float* %".1102"
  %".1104" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 50
  store float 0x3ff0000000000000, float* %".1104"
  %".1106" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 51
  store float 0x3ff0000000000000, float* %".1106"
  %".1108" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 52
  store float 0x3ff0000000000000, float* %".1108"
  %".1110" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 53
  store float 0x3ff0000000000000, float* %".1110"
  %".1112" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 54
  store float 0x3ff0000000000000, float* %".1112"
  %".1114" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 55
  store float 0x3ff0000000000000, float* %".1114"
  %".1116" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 56
  store float 0x3ff0000000000000, float* %".1116"
  %".1118" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 57
  store float 0x3ff0000000000000, float* %".1118"
  %".1120" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 58
  store float 0x3ff0000000000000, float* %".1120"
  %".1122" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 59
  store float 0x3ff0000000000000, float* %".1122"
  %".1124" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 60
  store float 0x3ff0000000000000, float* %".1124"
  %".1126" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 61
  store float 0x3ff0000000000000, float* %".1126"
  %".1128" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 62
  store float 0x3ff0000000000000, float* %".1128"
  %".1130" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 63
  store float 0x3ff0000000000000, float* %".1130"
  %".1132" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 64
  store float 0x3ff0000000000000, float* %".1132"
  %".1134" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 65
  store float 0x3ff0000000000000, float* %".1134"
  %".1136" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 66
  store float 0x3ff0000000000000, float* %".1136"
  %".1138" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 67
  store float 0x3ff0000000000000, float* %".1138"
  %".1140" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 68
  store float 0x3ff0000000000000, float* %".1140"
  %".1142" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 69
  store float 0x3ff0000000000000, float* %".1142"
  %".1144" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 70
  store float 0x3ff0000000000000, float* %".1144"
  %".1146" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 71
  store float 0x3ff0000000000000, float* %".1146"
  %".1148" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 72
  store float 0x3ff0000000000000, float* %".1148"
  %".1150" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 73
  store float 0x3ff0000000000000, float* %".1150"
  %".1152" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 74
  store float 0x3ff0000000000000, float* %".1152"
  %".1154" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 75
  store float 0x3ff0000000000000, float* %".1154"
  %".1156" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 76
  store float 0x3ff0000000000000, float* %".1156"
  %".1158" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 77
  store float 0x3ff0000000000000, float* %".1158"
  %".1160" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 78
  store float 0x3ff0000000000000, float* %".1160"
  %".1162" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 79
  store float 0x3ff0000000000000, float* %".1162"
  %".1164" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 80
  store float 0x3ff0000000000000, float* %".1164"
  %".1166" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 81
  store float 0x3ff0000000000000, float* %".1166"
  %".1168" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 82
  store float 0x3ff0000000000000, float* %".1168"
  %".1170" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 83
  store float 0x3ff0000000000000, float* %".1170"
  %".1172" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 84
  store float 0x3ff0000000000000, float* %".1172"
  %".1174" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 85
  store float 0x3ff0000000000000, float* %".1174"
  %".1176" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 86
  store float 0x3ff0000000000000, float* %".1176"
  %".1178" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 87
  store float 0x3ff0000000000000, float* %".1178"
  %".1180" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 88
  store float 0x3ff0000000000000, float* %".1180"
  %".1182" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 89
  store float 0x3ff0000000000000, float* %".1182"
  %".1184" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 90
  store float 0x3ff0000000000000, float* %".1184"
  %".1186" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 91
  store float 0x3ff0000000000000, float* %".1186"
  %".1188" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 92
  store float 0x3ff0000000000000, float* %".1188"
  %".1190" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 93
  store float 0x3ff0000000000000, float* %".1190"
  %".1192" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 94
  store float 0x3ff0000000000000, float* %".1192"
  %".1194" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 95
  store float 0x3ff0000000000000, float* %".1194"
  %".1196" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 96
  store float 0x3ff0000000000000, float* %".1196"
  %".1198" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 97
  store float 0x3ff0000000000000, float* %".1198"
  %".1200" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 98
  store float 0x3ff0000000000000, float* %".1200"
  %".1202" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 99
  store float 0x3ff0000000000000, float* %".1202"
  %".1204" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 100
  store float 0x3ff0000000000000, float* %".1204"
  %".1206" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 101
  store float 0x3ff0000000000000, float* %".1206"
  %".1208" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 102
  store float 0x3ff0000000000000, float* %".1208"
  %".1210" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 103
  store float 0x3ff0000000000000, float* %".1210"
  %".1212" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 104
  store float 0x3ff0000000000000, float* %".1212"
  %".1214" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 105
  store float 0x3ff0000000000000, float* %".1214"
  %".1216" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 106
  store float 0x3ff0000000000000, float* %".1216"
  %".1218" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 107
  store float 0x3ff0000000000000, float* %".1218"
  %".1220" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 108
  store float 0x3ff0000000000000, float* %".1220"
  %".1222" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 109
  store float 0x3ff0000000000000, float* %".1222"
  %".1224" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 110
  store float 0x3ff0000000000000, float* %".1224"
  %".1226" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 111
  store float 0x3ff0000000000000, float* %".1226"
  %".1228" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 112
  store float 0x3ff0000000000000, float* %".1228"
  %".1230" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 113
  store float 0x3ff0000000000000, float* %".1230"
  %".1232" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 114
  store float 0x3ff0000000000000, float* %".1232"
  %".1234" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 115
  store float 0x3ff0000000000000, float* %".1234"
  %".1236" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 116
  store float 0x3ff0000000000000, float* %".1236"
  %".1238" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 117
  store float 0x3ff0000000000000, float* %".1238"
  %".1240" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 118
  store float 0x3ff0000000000000, float* %".1240"
  %".1242" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 119
  store float 0x3ff0000000000000, float* %".1242"
  %".1244" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 120
  store float 0x3ff0000000000000, float* %".1244"
  %".1246" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 121
  store float 0x3ff0000000000000, float* %".1246"
  %".1248" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 122
  store float 0x3ff0000000000000, float* %".1248"
  %".1250" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 123
  store float 0x3ff0000000000000, float* %".1250"
  %".1252" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 124
  store float 0x3ff0000000000000, float* %".1252"
  %".1254" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 125
  store float 0x3ff0000000000000, float* %".1254"
  %".1256" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 126
  store float 0x3ff0000000000000, float* %".1256"
  %".1258" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 127
  store float 0x3ff0000000000000, float* %".1258"
  %".1260" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 128
  store float 0x3ff0000000000000, float* %".1260"
  %".1262" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 129
  store float 0x3ff0000000000000, float* %".1262"
  %".1264" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 130
  store float 0x3ff0000000000000, float* %".1264"
  %".1266" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 131
  store float 0x3ff0000000000000, float* %".1266"
  %".1268" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 132
  store float 0x3ff0000000000000, float* %".1268"
  %".1270" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 133
  store float 0x3ff0000000000000, float* %".1270"
  %".1272" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 134
  store float 0x3ff0000000000000, float* %".1272"
  %".1274" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 135
  store float 0x3ff0000000000000, float* %".1274"
  %".1276" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 136
  store float 0x3ff0000000000000, float* %".1276"
  %".1278" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 137
  store float 0x3ff0000000000000, float* %".1278"
  %".1280" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 138
  store float 0x3ff0000000000000, float* %".1280"
  %".1282" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 139
  store float 0x3ff0000000000000, float* %".1282"
  %".1284" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 140
  store float 0x3ff0000000000000, float* %".1284"
  %".1286" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 141
  store float 0x3ff0000000000000, float* %".1286"
  %".1288" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 142
  store float 0x3ff0000000000000, float* %".1288"
  %".1290" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 143
  store float 0x3ff0000000000000, float* %".1290"
  %".1292" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 144
  store float 0x3ff0000000000000, float* %".1292"
  %".1294" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 145
  store float 0x3ff0000000000000, float* %".1294"
  %".1296" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 146
  store float 0x3ff0000000000000, float* %".1296"
  %".1298" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 147
  store float 0x3ff0000000000000, float* %".1298"
  %".1300" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 148
  store float 0x3ff0000000000000, float* %".1300"
  %".1302" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 149
  store float 0x3ff0000000000000, float* %".1302"
  %".1304" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 150
  store float 0x3ff0000000000000, float* %".1304"
  %".1306" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 151
  store float 0x3ff0000000000000, float* %".1306"
  %".1308" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 152
  store float 0x3ff0000000000000, float* %".1308"
  %".1310" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 153
  store float 0x3ff0000000000000, float* %".1310"
  %".1312" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 154
  store float 0x3ff0000000000000, float* %".1312"
  %".1314" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 155
  store float 0x3ff0000000000000, float* %".1314"
  %".1316" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 156
  store float 0x3ff0000000000000, float* %".1316"
  %".1318" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 157
  store float 0x3ff0000000000000, float* %".1318"
  %".1320" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 158
  store float 0x3ff0000000000000, float* %".1320"
  %".1322" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 159
  store float 0x3ff0000000000000, float* %".1322"
  %".1324" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 160
  store float 0x3ff0000000000000, float* %".1324"
  %".1326" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 161
  store float 0x3ff0000000000000, float* %".1326"
  %".1328" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 162
  store float 0x3ff0000000000000, float* %".1328"
  %".1330" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 163
  store float 0x3ff0000000000000, float* %".1330"
  %".1332" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 164
  store float 0x3ff0000000000000, float* %".1332"
  %".1334" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 165
  store float 0x3ff0000000000000, float* %".1334"
  %".1336" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 166
  store float 0x3ff0000000000000, float* %".1336"
  %".1338" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 167
  store float 0x3ff0000000000000, float* %".1338"
  %".1340" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 168
  store float 0x3ff0000000000000, float* %".1340"
  %".1342" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 169
  store float 0x3ff0000000000000, float* %".1342"
  %".1344" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 170
  store float 0x3ff0000000000000, float* %".1344"
  %".1346" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 171
  store float 0x3ff0000000000000, float* %".1346"
  %".1348" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 172
  store float 0x3ff0000000000000, float* %".1348"
  %".1350" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 173
  store float 0x3ff0000000000000, float* %".1350"
  %".1352" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 174
  store float 0x3ff0000000000000, float* %".1352"
  %".1354" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 175
  store float 0x3ff0000000000000, float* %".1354"
  %".1356" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 176
  store float 0x3ff0000000000000, float* %".1356"
  %".1358" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 177
  store float 0x3ff0000000000000, float* %".1358"
  %".1360" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 178
  store float 0x3ff0000000000000, float* %".1360"
  %".1362" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 179
  store float 0x3ff0000000000000, float* %".1362"
  %".1364" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 180
  store float 0x3ff0000000000000, float* %".1364"
  %".1366" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 181
  store float 0x3ff0000000000000, float* %".1366"
  %".1368" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 182
  store float 0x3ff0000000000000, float* %".1368"
  %".1370" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 183
  store float 0x3ff0000000000000, float* %".1370"
  %".1372" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 184
  store float 0x3ff0000000000000, float* %".1372"
  %".1374" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 185
  store float 0x3ff0000000000000, float* %".1374"
  %".1376" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 186
  store float 0x3ff0000000000000, float* %".1376"
  %".1378" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 187
  store float 0x3ff0000000000000, float* %".1378"
  %".1380" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 188
  store float 0x3ff0000000000000, float* %".1380"
  %".1382" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 189
  store float 0x3ff0000000000000, float* %".1382"
  %".1384" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 190
  store float 0x3ff0000000000000, float* %".1384"
  %".1386" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 191
  store float 0x3ff0000000000000, float* %".1386"
  %".1388" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 192
  store float 0x3ff0000000000000, float* %".1388"
  %".1390" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 193
  store float 0x3ff0000000000000, float* %".1390"
  %".1392" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 194
  store float 0x3ff0000000000000, float* %".1392"
  %".1394" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 195
  store float 0x3ff0000000000000, float* %".1394"
  %".1396" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 196
  store float 0x3ff0000000000000, float* %".1396"
  %".1398" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 197
  store float 0x3ff0000000000000, float* %".1398"
  %".1400" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 198
  store float 0x3ff0000000000000, float* %".1400"
  %".1402" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 199
  store float 0x3ff0000000000000, float* %".1402"
  %".1404" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 200
  store float 0x3ff0000000000000, float* %".1404"
  %".1406" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 201
  store float 0x3ff0000000000000, float* %".1406"
  %".1408" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 202
  store float 0x3ff0000000000000, float* %".1408"
  %".1410" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 203
  store float 0x3ff0000000000000, float* %".1410"
  %".1412" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 204
  store float 0x3ff0000000000000, float* %".1412"
  %".1414" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 205
  store float 0x3ff0000000000000, float* %".1414"
  %".1416" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 206
  store float 0x3ff0000000000000, float* %".1416"
  %".1418" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 207
  store float 0x3ff0000000000000, float* %".1418"
  %".1420" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 208
  store float 0x3ff0000000000000, float* %".1420"
  %".1422" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 209
  store float 0x3ff0000000000000, float* %".1422"
  %".1424" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 210
  store float 0x3ff0000000000000, float* %".1424"
  %".1426" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 211
  store float 0x3ff0000000000000, float* %".1426"
  %".1428" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 212
  store float 0x3ff0000000000000, float* %".1428"
  %".1430" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 213
  store float 0x3ff0000000000000, float* %".1430"
  %".1432" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 214
  store float 0x3ff0000000000000, float* %".1432"
  %".1434" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 215
  store float 0x3ff0000000000000, float* %".1434"
  %".1436" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 216
  store float 0x3ff0000000000000, float* %".1436"
  %".1438" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 217
  store float 0x3ff0000000000000, float* %".1438"
  %".1440" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 218
  store float 0x3ff0000000000000, float* %".1440"
  %".1442" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 219
  store float 0x3ff0000000000000, float* %".1442"
  %".1444" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 220
  store float 0x3ff0000000000000, float* %".1444"
  %".1446" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 221
  store float 0x3ff0000000000000, float* %".1446"
  %".1448" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 222
  store float 0x3ff0000000000000, float* %".1448"
  %".1450" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 223
  store float 0x3ff0000000000000, float* %".1450"
  %".1452" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 224
  store float 0x3ff0000000000000, float* %".1452"
  %".1454" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 225
  store float 0x3ff0000000000000, float* %".1454"
  %".1456" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 226
  store float 0x3ff0000000000000, float* %".1456"
  %".1458" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 227
  store float 0x3ff0000000000000, float* %".1458"
  %".1460" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 228
  store float 0x3ff0000000000000, float* %".1460"
  %".1462" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 229
  store float 0x3ff0000000000000, float* %".1462"
  %".1464" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 230
  store float 0x3ff0000000000000, float* %".1464"
  %".1466" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 231
  store float 0x3ff0000000000000, float* %".1466"
  %".1468" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 232
  store float 0x3ff0000000000000, float* %".1468"
  %".1470" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 233
  store float 0x3ff0000000000000, float* %".1470"
  %".1472" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 234
  store float 0x3ff0000000000000, float* %".1472"
  %".1474" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 235
  store float 0x3ff0000000000000, float* %".1474"
  %".1476" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 236
  store float 0x3ff0000000000000, float* %".1476"
  %".1478" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 237
  store float 0x3ff0000000000000, float* %".1478"
  %".1480" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 238
  store float 0x3ff0000000000000, float* %".1480"
  %".1482" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 239
  store float 0x3ff0000000000000, float* %".1482"
  %".1484" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 240
  store float 0x3ff0000000000000, float* %".1484"
  %".1486" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 241
  store float 0x3ff0000000000000, float* %".1486"
  %".1488" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 242
  store float 0x3ff0000000000000, float* %".1488"
  %".1490" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 243
  store float 0x3ff0000000000000, float* %".1490"
  %".1492" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 244
  store float 0x3ff0000000000000, float* %".1492"
  %".1494" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 245
  store float 0x3ff0000000000000, float* %".1494"
  %".1496" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 246
  store float 0x3ff0000000000000, float* %".1496"
  %".1498" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 247
  store float 0x3ff0000000000000, float* %".1498"
  %".1500" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 248
  store float 0x3ff0000000000000, float* %".1500"
  %".1502" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 249
  store float 0x3ff0000000000000, float* %".1502"
  %".1504" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 250
  store float 0x3ff0000000000000, float* %".1504"
  %".1506" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 251
  store float 0x3ff0000000000000, float* %".1506"
  %".1508" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 252
  store float 0x3ff0000000000000, float* %".1508"
  %".1510" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 253
  store float 0x3ff0000000000000, float* %".1510"
  %".1512" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 254
  store float 0x3ff0000000000000, float* %".1512"
  %".1514" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 255
  store float 0x3ff0000000000000, float* %".1514"
  %".1516" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 256
  store float 0x3ff0000000000000, float* %".1516"
  %".1518" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 257
  store float 0x3ff0000000000000, float* %".1518"
  %".1520" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 258
  store float 0x3ff0000000000000, float* %".1520"
  %".1522" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 259
  store float 0x3ff0000000000000, float* %".1522"
  %".1524" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 260
  store float 0x3ff0000000000000, float* %".1524"
  %".1526" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 261
  store float 0x3ff0000000000000, float* %".1526"
  %".1528" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 262
  store float 0x3ff0000000000000, float* %".1528"
  %".1530" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 263
  store float 0x3ff0000000000000, float* %".1530"
  %".1532" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 264
  store float 0x3ff0000000000000, float* %".1532"
  %".1534" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 265
  store float 0x3ff0000000000000, float* %".1534"
  %".1536" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 266
  store float 0x3ff0000000000000, float* %".1536"
  %".1538" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 267
  store float 0x3ff0000000000000, float* %".1538"
  %".1540" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 268
  store float 0x3ff0000000000000, float* %".1540"
  %".1542" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 269
  store float 0x3ff0000000000000, float* %".1542"
  %".1544" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 270
  store float 0x3ff0000000000000, float* %".1544"
  %".1546" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 271
  store float 0x3ff0000000000000, float* %".1546"
  %".1548" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 272
  store float 0x3ff0000000000000, float* %".1548"
  %".1550" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 273
  store float 0x3ff0000000000000, float* %".1550"
  %".1552" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 274
  store float 0x3ff0000000000000, float* %".1552"
  %".1554" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 275
  store float 0x3ff0000000000000, float* %".1554"
  %".1556" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 276
  store float 0x3ff0000000000000, float* %".1556"
  %".1558" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 277
  store float 0x3ff0000000000000, float* %".1558"
  %".1560" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 278
  store float 0x3ff0000000000000, float* %".1560"
  %".1562" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 279
  store float 0x3ff0000000000000, float* %".1562"
  %".1564" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 280
  store float 0x3ff0000000000000, float* %".1564"
  %".1566" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 281
  store float 0x3ff0000000000000, float* %".1566"
  %".1568" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 282
  store float 0x3ff0000000000000, float* %".1568"
  %".1570" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 283
  store float 0x3ff0000000000000, float* %".1570"
  %".1572" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 284
  store float 0x3ff0000000000000, float* %".1572"
  %".1574" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 285
  store float 0x3ff0000000000000, float* %".1574"
  %".1576" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 286
  store float 0x3ff0000000000000, float* %".1576"
  %".1578" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 287
  store float 0x3ff0000000000000, float* %".1578"
  %".1580" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 288
  store float 0x3ff0000000000000, float* %".1580"
  %".1582" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 289
  store float 0x3ff0000000000000, float* %".1582"
  %".1584" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 290
  store float 0x3ff0000000000000, float* %".1584"
  %".1586" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 291
  store float 0x3ff0000000000000, float* %".1586"
  %".1588" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 292
  store float 0x3ff0000000000000, float* %".1588"
  %".1590" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 293
  store float 0x3ff0000000000000, float* %".1590"
  %".1592" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 294
  store float 0x3ff0000000000000, float* %".1592"
  %".1594" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 295
  store float 0x3ff0000000000000, float* %".1594"
  %".1596" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 296
  store float 0x3ff0000000000000, float* %".1596"
  %".1598" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 297
  store float 0x3ff0000000000000, float* %".1598"
  %".1600" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 298
  store float 0x3ff0000000000000, float* %".1600"
  %".1602" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 299
  store float 0x3ff0000000000000, float* %".1602"
  %".1604" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 300
  store float 0x3ff0000000000000, float* %".1604"
  %".1606" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 301
  store float 0x3ff0000000000000, float* %".1606"
  %".1608" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 302
  store float 0x3ff0000000000000, float* %".1608"
  %".1610" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 303
  store float 0x3ff0000000000000, float* %".1610"
  %".1612" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 304
  store float 0x3ff0000000000000, float* %".1612"
  %".1614" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 305
  store float 0x3ff0000000000000, float* %".1614"
  %".1616" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 306
  store float 0x3ff0000000000000, float* %".1616"
  %".1618" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 307
  store float 0x3ff0000000000000, float* %".1618"
  %".1620" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 308
  store float 0x3ff0000000000000, float* %".1620"
  %".1622" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 309
  store float 0x3ff0000000000000, float* %".1622"
  %".1624" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 310
  store float 0x3ff0000000000000, float* %".1624"
  %".1626" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 311
  store float 0x3ff0000000000000, float* %".1626"
  %".1628" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 312
  store float 0x3ff0000000000000, float* %".1628"
  %".1630" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 313
  store float 0x3ff0000000000000, float* %".1630"
  %".1632" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 314
  store float 0x3ff0000000000000, float* %".1632"
  %".1634" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 315
  store float 0x3ff0000000000000, float* %".1634"
  %".1636" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 316
  store float 0x3ff0000000000000, float* %".1636"
  %".1638" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 317
  store float 0x3ff0000000000000, float* %".1638"
  %".1640" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 318
  store float 0x3ff0000000000000, float* %".1640"
  %".1642" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 319
  store float 0x3ff0000000000000, float* %".1642"
  %".1644" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 320
  store float 0x3ff0000000000000, float* %".1644"
  %".1646" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 321
  store float 0x3ff0000000000000, float* %".1646"
  %".1648" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 322
  store float 0x3ff0000000000000, float* %".1648"
  %".1650" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 323
  store float 0x3ff0000000000000, float* %".1650"
  %".1652" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 324
  store float 0x3ff0000000000000, float* %".1652"
  %".1654" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 325
  store float 0x3ff0000000000000, float* %".1654"
  %".1656" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 326
  store float 0x3ff0000000000000, float* %".1656"
  %".1658" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 327
  store float 0x3ff0000000000000, float* %".1658"
  %".1660" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 328
  store float 0x3ff0000000000000, float* %".1660"
  %".1662" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 329
  store float 0x3ff0000000000000, float* %".1662"
  %".1664" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 330
  store float 0x3ff0000000000000, float* %".1664"
  %".1666" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 331
  store float 0x3ff0000000000000, float* %".1666"
  %".1668" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 332
  store float 0x3ff0000000000000, float* %".1668"
  %".1670" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 333
  store float 0x3ff0000000000000, float* %".1670"
  %".1672" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 334
  store float 0x3ff0000000000000, float* %".1672"
  %".1674" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 335
  store float 0x3ff0000000000000, float* %".1674"
  %".1676" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 336
  store float 0x3ff0000000000000, float* %".1676"
  %".1678" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 337
  store float 0x3ff0000000000000, float* %".1678"
  %".1680" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 338
  store float 0x3ff0000000000000, float* %".1680"
  %".1682" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 339
  store float 0x3ff0000000000000, float* %".1682"
  %".1684" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 340
  store float 0x3ff0000000000000, float* %".1684"
  %".1686" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 341
  store float 0x3ff0000000000000, float* %".1686"
  %".1688" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 342
  store float 0x3ff0000000000000, float* %".1688"
  %".1690" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 343
  store float 0x3ff0000000000000, float* %".1690"
  %".1692" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 344
  store float 0x3ff0000000000000, float* %".1692"
  %".1694" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 345
  store float 0x3ff0000000000000, float* %".1694"
  %".1696" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 346
  store float 0x3ff0000000000000, float* %".1696"
  %".1698" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 347
  store float 0x3ff0000000000000, float* %".1698"
  %".1700" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 348
  store float 0x3ff0000000000000, float* %".1700"
  %".1702" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 349
  store float 0x3ff0000000000000, float* %".1702"
  %".1704" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 350
  store float 0x3ff0000000000000, float* %".1704"
  %".1706" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 351
  store float 0x3ff0000000000000, float* %".1706"
  %".1708" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 352
  store float 0x3ff0000000000000, float* %".1708"
  %".1710" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 353
  store float 0x3ff0000000000000, float* %".1710"
  %".1712" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 354
  store float 0x3ff0000000000000, float* %".1712"
  %".1714" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 355
  store float 0x3ff0000000000000, float* %".1714"
  %".1716" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 356
  store float 0x3ff0000000000000, float* %".1716"
  %".1718" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 357
  store float 0x3ff0000000000000, float* %".1718"
  %".1720" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 358
  store float 0x3ff0000000000000, float* %".1720"
  %".1722" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 359
  store float 0x3ff0000000000000, float* %".1722"
  %".1724" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 360
  store float 0x3ff0000000000000, float* %".1724"
  %".1726" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 361
  store float 0x3ff0000000000000, float* %".1726"
  %".1728" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 362
  store float 0x3ff0000000000000, float* %".1728"
  %".1730" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 363
  store float 0x3ff0000000000000, float* %".1730"
  %".1732" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 364
  store float 0x3ff0000000000000, float* %".1732"
  %".1734" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 365
  store float 0x3ff0000000000000, float* %".1734"
  %".1736" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 366
  store float 0x3ff0000000000000, float* %".1736"
  %".1738" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 367
  store float 0x3ff0000000000000, float* %".1738"
  %".1740" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 368
  store float 0x3ff0000000000000, float* %".1740"
  %".1742" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 369
  store float 0x3ff0000000000000, float* %".1742"
  %".1744" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 370
  store float 0x3ff0000000000000, float* %".1744"
  %".1746" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 371
  store float 0x3ff0000000000000, float* %".1746"
  %".1748" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 372
  store float 0x3ff0000000000000, float* %".1748"
  %".1750" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 373
  store float 0x3ff0000000000000, float* %".1750"
  %".1752" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 374
  store float 0x3ff0000000000000, float* %".1752"
  %".1754" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 375
  store float 0x3ff0000000000000, float* %".1754"
  %".1756" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 376
  store float 0x3ff0000000000000, float* %".1756"
  %".1758" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 377
  store float 0x3ff0000000000000, float* %".1758"
  %".1760" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 378
  store float 0x3ff0000000000000, float* %".1760"
  %".1762" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 379
  store float 0x3ff0000000000000, float* %".1762"
  %".1764" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 380
  store float 0x3ff0000000000000, float* %".1764"
  %".1766" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 381
  store float 0x3ff0000000000000, float* %".1766"
  %".1768" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 382
  store float 0x3ff0000000000000, float* %".1768"
  %".1770" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 383
  store float 0x3ff0000000000000, float* %".1770"
  %".1772" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 384
  store float 0x3ff0000000000000, float* %".1772"
  %".1774" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 385
  store float 0x3ff0000000000000, float* %".1774"
  %".1776" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 386
  store float 0x3ff0000000000000, float* %".1776"
  %".1778" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 387
  store float 0x3ff0000000000000, float* %".1778"
  %".1780" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 388
  store float 0x3ff0000000000000, float* %".1780"
  %".1782" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 389
  store float 0x3ff0000000000000, float* %".1782"
  %".1784" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 390
  store float 0x3ff0000000000000, float* %".1784"
  %".1786" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 391
  store float 0x3ff0000000000000, float* %".1786"
  %".1788" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 392
  store float 0x3ff0000000000000, float* %".1788"
  %".1790" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 393
  store float 0x3ff0000000000000, float* %".1790"
  %".1792" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 394
  store float 0x3ff0000000000000, float* %".1792"
  %".1794" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 395
  store float 0x3ff0000000000000, float* %".1794"
  %".1796" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 396
  store float 0x3ff0000000000000, float* %".1796"
  %".1798" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 397
  store float 0x3ff0000000000000, float* %".1798"
  %".1800" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 398
  store float 0x3ff0000000000000, float* %".1800"
  %".1802" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 399
  store float 0x3ff0000000000000, float* %".1802"
  %".1804" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 400
  store float 0x3ff0000000000000, float* %".1804"
  %".1806" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 401
  store float 0x3ff0000000000000, float* %".1806"
  %".1808" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 402
  store float 0x3ff0000000000000, float* %".1808"
  %".1810" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 403
  store float 0x3ff0000000000000, float* %".1810"
  %".1812" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 404
  store float 0x3ff0000000000000, float* %".1812"
  %".1814" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 405
  store float 0x3ff0000000000000, float* %".1814"
  %".1816" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 406
  store float 0x3ff0000000000000, float* %".1816"
  %".1818" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 407
  store float 0x3ff0000000000000, float* %".1818"
  %".1820" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 408
  store float 0x3ff0000000000000, float* %".1820"
  %".1822" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 409
  store float 0x3ff0000000000000, float* %".1822"
  %".1824" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 410
  store float 0x3ff0000000000000, float* %".1824"
  %".1826" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 411
  store float 0x3ff0000000000000, float* %".1826"
  %".1828" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 412
  store float 0x3ff0000000000000, float* %".1828"
  %".1830" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 413
  store float 0x3ff0000000000000, float* %".1830"
  %".1832" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 414
  store float 0x3ff0000000000000, float* %".1832"
  %".1834" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 415
  store float 0x3ff0000000000000, float* %".1834"
  %".1836" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 416
  store float 0x3ff0000000000000, float* %".1836"
  %".1838" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 417
  store float 0x3ff0000000000000, float* %".1838"
  %".1840" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 418
  store float 0x3ff0000000000000, float* %".1840"
  %".1842" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 419
  store float 0x3ff0000000000000, float* %".1842"
  %".1844" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 420
  store float 0x3ff0000000000000, float* %".1844"
  %".1846" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 421
  store float 0x3ff0000000000000, float* %".1846"
  %".1848" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 422
  store float 0x3ff0000000000000, float* %".1848"
  %".1850" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 423
  store float 0x3ff0000000000000, float* %".1850"
  %".1852" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 424
  store float 0x3ff0000000000000, float* %".1852"
  %".1854" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 425
  store float 0x3ff0000000000000, float* %".1854"
  %".1856" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 426
  store float 0x3ff0000000000000, float* %".1856"
  %".1858" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 427
  store float 0x3ff0000000000000, float* %".1858"
  %".1860" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 428
  store float 0x3ff0000000000000, float* %".1860"
  %".1862" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 429
  store float 0x3ff0000000000000, float* %".1862"
  %".1864" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 430
  store float 0x3ff0000000000000, float* %".1864"
  %".1866" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 431
  store float 0x3ff0000000000000, float* %".1866"
  %".1868" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 432
  store float 0x3ff0000000000000, float* %".1868"
  %".1870" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 433
  store float 0x3ff0000000000000, float* %".1870"
  %".1872" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 434
  store float 0x3ff0000000000000, float* %".1872"
  %".1874" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 435
  store float 0x3ff0000000000000, float* %".1874"
  %".1876" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 436
  store float 0x3ff0000000000000, float* %".1876"
  %".1878" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 437
  store float 0x3ff0000000000000, float* %".1878"
  %".1880" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 438
  store float 0x3ff0000000000000, float* %".1880"
  %".1882" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 439
  store float 0x3ff0000000000000, float* %".1882"
  %".1884" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 440
  store float 0x3ff0000000000000, float* %".1884"
  %".1886" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 441
  store float 0x3ff0000000000000, float* %".1886"
  %".1888" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 442
  store float 0x3ff0000000000000, float* %".1888"
  %".1890" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 443
  store float 0x3ff0000000000000, float* %".1890"
  %".1892" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 444
  store float 0x3ff0000000000000, float* %".1892"
  %".1894" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 445
  store float 0x3ff0000000000000, float* %".1894"
  %".1896" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 446
  store float 0x3ff0000000000000, float* %".1896"
  %".1898" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 447
  store float 0x3ff0000000000000, float* %".1898"
  %".1900" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 448
  store float 0x3ff0000000000000, float* %".1900"
  %".1902" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 449
  store float 0x3ff0000000000000, float* %".1902"
  %".1904" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 450
  store float 0x3ff0000000000000, float* %".1904"
  %".1906" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 451
  store float 0x3ff0000000000000, float* %".1906"
  %".1908" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 452
  store float 0x3ff0000000000000, float* %".1908"
  %".1910" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 453
  store float 0x3ff0000000000000, float* %".1910"
  %".1912" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 454
  store float 0x3ff0000000000000, float* %".1912"
  %".1914" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 455
  store float 0x3ff0000000000000, float* %".1914"
  %".1916" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 456
  store float 0x3ff0000000000000, float* %".1916"
  %".1918" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 457
  store float 0x3ff0000000000000, float* %".1918"
  %".1920" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 458
  store float 0x3ff0000000000000, float* %".1920"
  %".1922" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 459
  store float 0x3ff0000000000000, float* %".1922"
  %".1924" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 460
  store float 0x3ff0000000000000, float* %".1924"
  %".1926" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 461
  store float 0x3ff0000000000000, float* %".1926"
  %".1928" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 462
  store float 0x3ff0000000000000, float* %".1928"
  %".1930" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 463
  store float 0x3ff0000000000000, float* %".1930"
  %".1932" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 464
  store float 0x3ff0000000000000, float* %".1932"
  %".1934" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 465
  store float 0x3ff0000000000000, float* %".1934"
  %".1936" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 466
  store float 0x3ff0000000000000, float* %".1936"
  %".1938" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 467
  store float 0x3ff0000000000000, float* %".1938"
  %".1940" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 468
  store float 0x3ff0000000000000, float* %".1940"
  %".1942" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 469
  store float 0x3ff0000000000000, float* %".1942"
  %".1944" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 470
  store float 0x3ff0000000000000, float* %".1944"
  %".1946" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 471
  store float 0x3ff0000000000000, float* %".1946"
  %".1948" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 472
  store float 0x3ff0000000000000, float* %".1948"
  %".1950" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 473
  store float 0x3ff0000000000000, float* %".1950"
  %".1952" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 474
  store float 0x3ff0000000000000, float* %".1952"
  %".1954" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 475
  store float 0x3ff0000000000000, float* %".1954"
  %".1956" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 476
  store float 0x3ff0000000000000, float* %".1956"
  %".1958" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 477
  store float 0x3ff0000000000000, float* %".1958"
  %".1960" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 478
  store float 0x3ff0000000000000, float* %".1960"
  %".1962" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 479
  store float 0x3ff0000000000000, float* %".1962"
  %".1964" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 480
  store float 0x3ff0000000000000, float* %".1964"
  %".1966" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 481
  store float 0x3ff0000000000000, float* %".1966"
  %".1968" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 482
  store float 0x3ff0000000000000, float* %".1968"
  %".1970" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 483
  store float 0x3ff0000000000000, float* %".1970"
  %".1972" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 484
  store float 0x3ff0000000000000, float* %".1972"
  %".1974" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 485
  store float 0x3ff0000000000000, float* %".1974"
  %".1976" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 486
  store float 0x3ff0000000000000, float* %".1976"
  %".1978" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 487
  store float 0x3ff0000000000000, float* %".1978"
  %".1980" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 488
  store float 0x3ff0000000000000, float* %".1980"
  %".1982" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 489
  store float 0x3ff0000000000000, float* %".1982"
  %".1984" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 490
  store float 0x3ff0000000000000, float* %".1984"
  %".1986" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 491
  store float 0x3ff0000000000000, float* %".1986"
  %".1988" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 492
  store float 0x3ff0000000000000, float* %".1988"
  %".1990" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 493
  store float 0x3ff0000000000000, float* %".1990"
  %".1992" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 494
  store float 0x3ff0000000000000, float* %".1992"
  %".1994" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 495
  store float 0x3ff0000000000000, float* %".1994"
  %".1996" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 496
  store float 0x3ff0000000000000, float* %".1996"
  %".1998" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 497
  store float 0x3ff0000000000000, float* %".1998"
  %".2000" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 498
  store float 0x3ff0000000000000, float* %".2000"
  %".2002" = getelementptr [500 x float], [500 x float]* %".1003", i32 0, i32 499
  store float 0x3ff0000000000000, float* %".2002"
  %".2004" = load [500 x float], [500 x float]* %".1003"
  %".2005" = call float @"process_data"([500 x float] %".2004")
  call void @"vyn_io_print_f32"(float %".2005")
  ret i32 0
}

define internal i1 @"exists"(i8* %".1")
{
entry:
  %"path" = alloca i8*
  store i8* %".1", i8** %"path"
  ret i1 0
}

@"str.0" = internal constant [13 x i8] c"process_data\00"
@"str.1" = internal constant [13 x i8] c"process_data\00"