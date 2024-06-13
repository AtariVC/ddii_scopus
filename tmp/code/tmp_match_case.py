def match_case(mode):
    match mode:
        case 0:
            mode = 1
            mode = 2
        case 1:
            print(1)
        case 2:
            print(2)

match_case(1)