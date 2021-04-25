import csv

ETH_TO_LDO_RATE_PRECISION = 10**18

# 100M LDO in 21600 ETH
# 4629.62962962963 LDO in one ETH
ETH_TO_LDO_RATE = ETH_TO_LDO_RATE_PRECISION * (100 * 10**6) // 21600

VESTING_CLIFF_DELAY = 1 * 60 * 60 * 24 * 365 # one year
VESTING_END_DELAY = 2 * 60 * 60 * 24 * 365 # two years
OFFER_EXPIRATION_DELAY = 2629746 # one month


def read_csv_purchasers(filename):
    data = [ (item[0], int(item[1])) for item in read_csv_data(filename) ]
    allocations_total = sum([ item[1] for item in data ])
    return (data, allocations_total)


def read_csv_data(filename):
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"', skipinitialspace=True)
        return list(reader)


(LDO_PURCHASERS, ALLOCATIONS_TOTAL) = read_csv_purchasers('purchasers.csv')
